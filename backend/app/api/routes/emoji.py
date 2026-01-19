from __future__ import annotations

import json
import secrets
import time

from fastapi import APIRouter, Query
from sqlmodel import func, select

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.api.errors import AppError
from app.api.schemas import (
    ApiEnvelope,
    EmojiCreateRequest,
    EmojiDetectData,
    EmojiDetectRequest,
    EmojiHistoryData,
    EmojiTaskData,
    OssUploadData,
)
from app.core.config import settings
from app.core.redis import get_redis
from app.integrations.aliyun_emoji import aliyun_emoji_client
from app.integrations.oss import generate_post_policy
from app.models import EmojiTask, EmojiTaskStatus, PointTransactionType, utc_now
from app.services.config_service import get_config

router = APIRouter(prefix="/emoji", tags=["emoji"])


@router.post("/upload", response_model=ApiEnvelope)
def upload(session: SessionDep, current_user: CurrentUser, ext: str = "jpg") -> ApiEnvelope:
    _ = session
    safe_ext = "".join([c for c in ext.lower() if c.isalnum()])[:10] or "jpg"
    ts = int(time.time())
    rand = secrets.token_hex(8)
    key = f"{settings.OSS_DIR_PREFIX}/{current_user.id}/{ts}_{rand}.{safe_ext}"
    policy = generate_post_policy(key=key, expire_seconds=settings.OSS_UPLOAD_EXPIRE_SECONDS)
    return ApiEnvelope(
        data=OssUploadData(
            host=policy.host,
            dir=policy.dir,
            key=policy.key,
            policy=policy.policy,
            signature=policy.signature,
            access_key_id=policy.access_key_id,
            expire_at=policy.expire_at,
            image_url=policy.image_url,
        )
    )


@router.post("/detect", response_model=ApiEnvelope)
def detect(session: SessionDep, current_user: CurrentUser, body: EmojiDetectRequest) -> ApiEnvelope:
    _ = session, current_user
    r = aliyun_emoji_client.detect(image_url=body.image_url)
    return ApiEnvelope(
        data=EmojiDetectData(passed=r.passed, face_bbox=r.face_bbox, ext_bbox=r.ext_bbox, raw=r.raw)
    )


@router.post("/create", response_model=ApiEnvelope)
def create(session: SessionDep, current_user: CurrentUser, body: EmojiCreateRequest) -> ApiEnvelope:
    cfg = get_config()
    points_cost = int(cfg.get("points_rules", {}).get("emoji", 200))

    face_bbox = body.face_bbox
    ext_bbox = body.ext_bbox
    raw_detect = None
    if not face_bbox or not ext_bbox:
        detect_r = aliyun_emoji_client.detect(image_url=body.image_url)
        if not detect_r.passed or not detect_r.face_bbox or not detect_r.ext_bbox:
            raise AppError(
                code=400101,
                message=detect_r.error_message or "Image detect failed",
                status_code=400,
            )
        face_bbox = detect_r.face_bbox
        ext_bbox = detect_r.ext_bbox
        raw_detect = detect_r.raw

    detect_result = {"face_bbox": face_bbox, "ext_bbox": ext_bbox, "raw": raw_detect}

    # Deduct points first (confirmed: even if generation fails, points are not refunded).
    crud.change_points(
        session=session,
        user_id=current_user.id,
        delta=-points_cost,
        tx_type=PointTransactionType.consume,
        task_type="emoji",
    )

    task = crud.create_emoji_task(
        session=session,
        user_id=current_user.id,
        image_url=body.image_url,
        driven_id=body.driven_id,
        detect_result=detect_result,
        points_cost=points_cost,
    )

    # Enqueue to Redis Streams for async processing.
    try:
        rds = get_redis()
        rds.xadd(
            "emoji_tasks",
            {
                "task_id": str(task.id),
                "user_id": str(current_user.id),
                "image_url": body.image_url,
                "driven_id": body.driven_id,
                "detect_result": json.dumps(detect_result),
            },
        )
    except Exception as e:
        # Task is created but can't be processed. Mark as failed and still return the task_id,
        # since points are consumed on task creation (even if it fails later).
        task.status = EmojiTaskStatus.failed
        task.error_message = f"Queue unavailable: {e}"
        task.completed_at = utc_now()
        session.add(task)
        session.commit()

    data = EmojiTaskData(
        id=task.id,
        status=task.status,
        points_cost=task.points_cost,
        result_url=task.result_url,
        error_message=task.error_message,
        created_at=task.created_at,
        completed_at=task.completed_at,
    )
    return ApiEnvelope(data=data)


@router.get("/task/{task_id}", response_model=ApiEnvelope)
def task_status(session: SessionDep, current_user: CurrentUser, task_id: int) -> ApiEnvelope:
    task = session.get(EmojiTask, task_id)
    if not task or task.user_id != current_user.id:
        raise AppError(code=404101, message="Task not found", status_code=404)
    data = EmojiTaskData(
        id=task.id,
        status=task.status,
        points_cost=task.points_cost,
        result_url=task.result_url,
        error_message=task.error_message,
        created_at=task.created_at,
        completed_at=task.completed_at,
    )
    return ApiEnvelope(data=data)


@router.get("/history", response_model=ApiEnvelope)
def history(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ApiEnvelope:
    offset = (page - 1) * page_size

    count_stmt = (
        select(func.count())
        .select_from(EmojiTask)
        .where(EmojiTask.user_id == current_user.id)
    )
    count = session.exec(count_stmt).one()

    stmt = (
        select(EmojiTask)
        .where(EmojiTask.user_id == current_user.id)
        .order_by(EmojiTask.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    tasks = session.exec(stmt).all()

    data = [
        EmojiTaskData(
            id=t.id,
            status=t.status,
            points_cost=t.points_cost,
            result_url=t.result_url,
            error_message=t.error_message,
            created_at=t.created_at,
            completed_at=t.completed_at,
        )
        for t in tasks
    ]
    return ApiEnvelope(data=EmojiHistoryData(data=data, count=count))


@router.delete("/task/{task_id}", response_model=ApiEnvelope)
def delete_task(session: SessionDep, current_user: CurrentUser, task_id: int) -> ApiEnvelope:
    task = session.get(EmojiTask, task_id)
    if not task or task.user_id != current_user.id:
        raise AppError(code=404101, message="Task not found", status_code=404)
    session.delete(task)
    session.commit()
    return ApiEnvelope(data={"deleted": True})
