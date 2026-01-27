"""
Emoji Worker - 异步处理表情包生成任务

从 Redis Streams 队列消费任务,调用阿里云 AI API 生成视频
"""

import asyncio
import json
import logging
import time
from datetime import datetime

from sqlmodel import Session, create_engine

from app.core.config import settings
from app.core.oss_client import get_oss_client
from app.core.redis_client import get_redis_client
from app.crud import get_emoji_task_by_id, update_emoji_task
from app.models import EmojiTaskUpdate
from app.services.emoji_service import get_emoji_service

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 创建数据库引擎
engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


async def process_emoji_task(task_id: int, task_data: dict) -> None:
    """
    处理单个表情包生成任务

    Args:
        task_id: 任务 ID
        task_data: 任务数据
    """
    logger.info(f"Processing task {task_id}")

    with Session(engine) as session:
        # 获取任务
        task = get_emoji_task_by_id(session=session, task_id=task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return

        try:
            # 更新状态为 processing
            update_emoji_task(
                session=session,
                db_task=task,
                task_in=EmojiTaskUpdate(status="processing"),
            )

            # 解析 bbox
            face_bbox = None
            ext_bbox = None

            if task_data.get("face_bbox"):
                try:
                    face_bbox = json.loads(task_data["face_bbox"])
                except Exception:
                    pass

            if task_data.get("ext_bbox"):
                try:
                    ext_bbox = json.loads(task_data["ext_bbox"])
                except Exception:
                    pass

            # 调用阿里云 AI API 创建视频生成任务
            emoji_service = get_emoji_service()
            create_result = await emoji_service.create_video_task(
                image_url=task_data["image_url"],
                driven_id=task_data["driven_id"],
                face_bbox=face_bbox,
                ext_bbox=ext_bbox,
            )

            if not create_result["success"]:
                # 创建任务失败
                update_emoji_task(
                    session=session,
                    db_task=task,
                    task_in=EmojiTaskUpdate(
                        status="failed",
                        error_message=create_result["error"],
                    ),
                )
                logger.error(f"Task {task_id} creation failed: {create_result['error']}")
                return

            ali_task_id = create_result["task_id"]
            logger.info(f"Task {task_id} created with ali_task_id: {ali_task_id}")

            # 更新阿里云任务 ID
            update_emoji_task(
                session=session,
                db_task=task,
                task_in=EmojiTaskUpdate(ali_task_id=ali_task_id),
            )

            # 轮询任务状态(建议间隔 15 秒)
            max_attempts = 40  # 最多轮询 10 分钟
            attempt = 0

            while attempt < max_attempts:
                await asyncio.sleep(15)  # 等待 15 秒
                attempt += 1

                status_result = await emoji_service.query_task_status(ali_task_id)

                if not status_result["success"]:
                    logger.warning(f"Task {task_id} status query failed: {status_result['error']}")
                    continue

                status = status_result["status"]
                logger.info(f"Task {task_id} status: {status}")

                if status == "SUCCEEDED":
                    # 生成成功
                    video_url = status_result["video_url"]

                    if video_url:
                        # 下载视频并转存到 OSS(视频有效期 24h)
                        try:
                            oss_client = get_oss_client()

                            # 下载视频
                            import httpx

                            async with httpx.AsyncClient(timeout=60.0) as client:
                                response = await client.get(video_url)
                                video_data = response.content

                            # 上传到 OSS
                            object_name = f"emoji/results/{task.user_id}/{datetime.utcnow().strftime('%Y%m%d')}/{task_id}.mp4"
                            result_url = oss_client.upload_file(
                                object_name=object_name,
                                file_data=video_data,
                                content_type="video/mp4",
                            )

                            # 更新任务状态
                            update_emoji_task(
                                session=session,
                                db_task=task,
                                task_in=EmojiTaskUpdate(
                                    status="completed",
                                    result_url=result_url,
                                    completed_at=datetime.utcnow(),
                                ),
                            )

                            logger.info(f"Task {task_id} completed successfully")
                        except Exception as e:
                            logger.error(f"Task {task_id} failed to save video: {e}")
                            update_emoji_task(
                                session=session,
                                db_task=task,
                                task_in=EmojiTaskUpdate(
                                    status="failed",
                                    error_message=f"Failed to save video: {str(e)}",
                                ),
                            )
                    else:
                        update_emoji_task(
                            session=session,
                            db_task=task,
                            task_in=EmojiTaskUpdate(
                                status="failed",
                                error_message="No video URL returned",
                            ),
                        )

                    break

                elif status == "FAILED":
                    # 生成失败
                    update_emoji_task(
                        session=session,
                        db_task=task,
                        task_in=EmojiTaskUpdate(
                            status="failed",
                            error_message=status_result.get("error", "Generation failed"),
                        ),
                    )
                    logger.error(f"Task {task_id} generation failed")
                    break

                elif status in ["PENDING", "RUNNING"]:
                    # 继续等待
                    continue

                else:
                    # 未知状态
                    logger.warning(f"Task {task_id} unknown status: {status}")
                    continue

            if attempt >= max_attempts:
                # 超时
                update_emoji_task(
                    session=session,
                    db_task=task,
                    task_in=EmojiTaskUpdate(
                        status="failed",
                        error_message="Task timeout after 10 minutes",
                    ),
                )
                logger.error(f"Task {task_id} timeout")

        except Exception as e:
            logger.error(f"Task {task_id} processing error: {e}")
            update_emoji_task(
                session=session,
                db_task=task,
                task_in=EmojiTaskUpdate(
                    status="failed",
                    error_message=str(e),
                ),
            )


async def consume_tasks() -> None:
    """
    从 Redis Streams 消费任务
    """
    redis_client = get_redis_client()
    # 按环境区分 stream key
    stream_key = f"emoji_tasks:{settings.ENVIRONMENT}"
    group_name = "emoji_workers"
    consumer_name = f"worker_{int(time.time())}"

    # 创建消费者组(如果不存在)
    redis_client.xgroup_create(stream_key, group_name, message_id="0", mkstream=True)

    logger.info(f"Worker {consumer_name} started, listening to {stream_key}")

    while True:
        try:
            # 从消费者组读取消息
            messages = redis_client.xreadgroup(
                group_name=group_name,
                consumer_name=consumer_name,
                streams={stream_key: ">"},
                count=1,
                block=5000,  # 阻塞 5 秒
            )

            if not messages:
                continue

            for stream, message_list in messages:
                for message_id, fields in message_list:
                    try:
                        task_id = int(fields["task_id"])
                        logger.info(f"Received task {task_id}")

                        # 处理任务
                        await process_emoji_task(task_id, fields)

                        # 确认消息
                        redis_client.xack(stream_key, group_name, message_id)
                        logger.info(f"Task {task_id} acknowledged")

                    except Exception as e:
                        logger.error(f"Failed to process message {message_id}: {e}")
                        # 不确认消息,让其他 worker 重试

        except KeyboardInterrupt:
            logger.info("Worker stopped by user")
            break
        except Exception as e:
            logger.error(f"Worker error: {e}")
            await asyncio.sleep(5)  # 等待 5 秒后重试


def main() -> None:
    """主函数"""
    logger.info("Starting Emoji Worker...")

    # 运行消费者
    asyncio.run(consume_tasks())


if __name__ == "__main__":
    main()
