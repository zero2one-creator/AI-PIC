from __future__ import annotations

import logging
import os
import time

from redis.exceptions import ResponseError
from sqlmodel import Session

from app.core.config import settings
from app.core.db import engine
from app.core.redis import get_redis
from app.enums import EmojiTaskStatus
from app.integrations.aliyun_emoji import aliyun_emoji_client
from app.integrations.oss import upload_from_url
from app.models import EmojiTask, utc_now

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("emoji_worker")

STREAM = "emoji_tasks"
GROUP = "emoji_worker"
CONSUMER = os.environ.get("EMOJI_WORKER_CONSUMER", "c1")


def ensure_consumer_group() -> None:
    r = get_redis()
    try:
        r.xgroup_create(STREAM, GROUP, id="0-0", mkstream=True)
    except ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise


def handle_task(task_id: int) -> None:
    with Session(engine) as session:
        task = session.get(EmojiTask, task_id)
        if not task:
            logger.warning("task not found: %s", task_id)
            return
        if task.status in (EmojiTaskStatus.completed, EmojiTaskStatus.failed):
            return

        task.status = EmojiTaskStatus.processing
        session.add(task)
        session.commit()

        if settings.ALIYUN_EMOJI_MOCK:
            task.result_url = "https://example.com/mock-result.mp4"
            task.status = EmojiTaskStatus.completed
            task.completed_at = utc_now()
            session.add(task)
            session.commit()
            return

        detect = task.detect_result or {}
        face_bbox = detect.get("face_bbox")
        ext_bbox = detect.get("ext_bbox")
        if not (isinstance(face_bbox, list) and isinstance(ext_bbox, list)):
            task.status = EmojiTaskStatus.failed
            task.error_message = "Missing face bbox from detect_result"
            task.completed_at = utc_now()
            session.add(task)
            session.commit()
            return

        # Create remote task if needed.
        if not task.aliyun_task_id:
            created = aliyun_emoji_client.create_task(
                image_url=task.source_image_url,
                driven_id=task.driven_id,
                face_bbox=face_bbox,
                ext_bbox=ext_bbox,
            )
            task.aliyun_task_id = created.task_id
            session.add(task)
            session.commit()

        start = time.time()
        while True:
            if time.time() - start > settings.EMOJI_POLL_TIMEOUT_SECONDS:
                task.status = EmojiTaskStatus.failed
                task.error_message = "DashScope task timeout"
                task.completed_at = utc_now()
                session.add(task)
                session.commit()
                return

            result = aliyun_emoji_client.get_task(task_id=task.aliyun_task_id)
            status = result.task_status.upper()

            if status == "SUCCEEDED":
                if not result.video_url:
                    task.status = EmojiTaskStatus.failed
                    task.error_message = "DashScope succeeded but missing video_url"
                    task.completed_at = utc_now()
                    session.add(task)
                    session.commit()
                    return

                key = f"{settings.OSS_RESULT_PREFIX}/{task.user_id}/{task.id}.mp4"
                try:
                    task.result_url = upload_from_url(url=result.video_url, key=key)
                except Exception as e:
                    task.status = EmojiTaskStatus.failed
                    task.error_message = f"OSS upload failed: {e}"
                    task.completed_at = utc_now()
                    session.add(task)
                    session.commit()
                    return

                task.status = EmojiTaskStatus.completed
                task.completed_at = utc_now()
                session.add(task)
                session.commit()
                return

            if status in ("FAILED", "CANCELED", "UNKNOWN"):
                task.status = EmojiTaskStatus.failed
                task.error_message = result.error_message or f"DashScope task {status}"
                task.completed_at = utc_now()
                session.add(task)
                session.commit()
                return

            time.sleep(max(1, settings.EMOJI_POLL_INTERVAL_SECONDS))


def main() -> None:
    ensure_consumer_group()
    r = get_redis()

    logger.info("emoji worker started: stream=%s group=%s consumer=%s", STREAM, GROUP, CONSUMER)

    while True:
        try:
            resp = r.xreadgroup(
                GROUP,
                CONSUMER,
                {STREAM: ">"},
                count=10,
                block=5000,
            )
            messages: list[tuple[str, dict[str, str]]] = []
            if resp:
                for _stream, batch in resp:
                    messages.extend(batch)
            else:
                # Reclaim stale pending messages (Redis 6.2+).
                try:
                    _next, claimed, _deleted = r.xautoclaim(
                        STREAM,
                        GROUP,
                        CONSUMER,
                        min_idle_time=60_000,
                        start_id="0-0",
                        count=10,
                    )
                    messages.extend(claimed)
                except Exception:
                    pass

            if not messages:
                continue

            for msg_id, fields in messages:
                try:
                    task_id = int(fields["task_id"])
                    handle_task(task_id)
                    r.xack(STREAM, GROUP, msg_id)
                except Exception as e:
                    logger.exception("failed processing message %s: %s", msg_id, e)
        except Exception as e:
            logger.exception("worker loop error: %s", e)
            time.sleep(1)


if __name__ == "__main__":  # pragma: no cover
    main()
