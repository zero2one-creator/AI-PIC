"""
Emoji 表情包生成 API 路由
"""

import json
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.core.config import settings
from app.core.oss_client import get_oss_client
from app.core.redis_client import get_redis_client
from app.models import EmojiTaskCreate, EmojiTaskPublic, EmojiTasksPublic, Message
from app.services.emoji_service import get_emoji_service

router = APIRouter(prefix="/emoji", tags=["emoji"])


@router.post("/upload")
async def upload_image(
    file: Annotated[UploadFile, File()],
    current_user: CurrentUser,
) -> dict:
    """
    上传图片到 OSS

    Returns:
        {"image_url": "https://..."}
    """
    try:
        # 验证文件类型
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Invalid file type. Only images are allowed.")

        # 读取文件内容
        file_data = await file.read()

        # 生成对象名称
        import uuid
        from datetime import datetime

        file_ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"
        object_name = f"emoji/uploads/{current_user.id}/{datetime.utcnow().strftime('%Y%m%d')}/{uuid.uuid4()}.{file_ext}"

        # 上传到 OSS
        oss_client = get_oss_client()
        image_url = oss_client.upload_file(
            object_name=object_name,
            file_data=file_data,
            content_type=file.content_type,
        )

        return {"image_url": image_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")


@router.post("/detect")
async def detect_image(
    image_url: str,
    current_user: CurrentUser,
) -> dict:
    """
    图像检测(人脸检测和内容审核)

    不扣积分,仅用于验证图片是否合规

    Returns:
        {
            "success": bool,
            "face_bbox": [x1, y1, x2, y2],
            "ext_bbox": [x1, y1, x2, y2],
            "error": str | None
        }
    """
    try:
        emoji_service = get_emoji_service()
        result = await emoji_service.detect_image(image_url)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to detect image: {str(e)}")


@router.post("/create", response_model=EmojiTaskPublic)
async def create_emoji_task(
    session: SessionDep,
    current_user: CurrentUser,
    image_url: str,
    driven_id: str,
    face_bbox: str | None = None,
    ext_bbox: str | None = None,
) -> EmojiTaskPublic:
    """
    创建表情包生成任务

    扣减积分并创建异步任务

    Args:
        image_url: 图片 URL
        driven_id: 驱动模板 ID
        face_bbox: 人脸框坐标 JSON 字符串
        ext_bbox: 扩展框坐标 JSON 字符串
    """
    # 检查并扣减积分
    points_cost = settings.POINTS_EMOJI_COST
    success, error = crud.consume_points(
        session=session,
        user_id=current_user.id,
        amount=points_cost,
        task_type="emoji",
    )

    if not success:
        raise HTTPException(status_code=400, detail=error)

    # 创建任务记录
    task_in = EmojiTaskCreate(
        user_id=current_user.id,
        task_type="emoji",
        source_image_url=image_url,
        driven_id=driven_id,
        face_bbox=face_bbox,
        ext_bbox=ext_bbox,
        status="pending",
        points_cost=points_cost,
    )

    task = crud.create_emoji_task(session=session, task_in=task_in)

    # 发送到 Redis Streams 队列 (按环境区分)
    from app.core.config import settings
    stream_key = f"emoji_tasks:{settings.ENVIRONMENT}"

    try:
        redis_client = get_redis_client()
        redis_client.xadd(
            stream_key=stream_key,
            fields={
                "task_id": str(task.id),
                "image_url": image_url,
                "driven_id": driven_id,
                "face_bbox": face_bbox or "",
                "ext_bbox": ext_bbox or "",
            },
        )
    except Exception as e:
        # 队列发送失败,记录日志但不影响任务创建
        import logging

        logging.error(f"Failed to send task to queue: {e}")

    return task


@router.get("/task/{task_id}", response_model=EmojiTaskPublic)
def get_emoji_task(
    session: SessionDep,
    current_user: CurrentUser,
    task_id: int,
) -> EmojiTaskPublic:
    """
    查询任务状态和结果
    """
    task = crud.get_emoji_task_by_id(session=session, task_id=task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 验证任务所有权
    if task.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized to access this task")

    return task


@router.get("/history", response_model=EmojiTasksPublic)
def get_emoji_history(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> EmojiTasksPublic:
    """
    获取生成历史记录(分页)
    """
    tasks = crud.get_user_emoji_tasks(
        session=session,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )

    return EmojiTasksPublic(
        data=tasks,
        count=len(tasks),
    )


@router.delete("/task/{task_id}", response_model=Message)
def delete_emoji_task(
    session: SessionDep,
    current_user: CurrentUser,
    task_id: int,
) -> Message:
    """
    删除生成记录
    """
    task = crud.get_emoji_task_by_id(session=session, task_id=task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 验证任务所有权
    if task.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized to delete this task")

    # 删除任务
    session.delete(task)
    session.commit()

    return Message(message="Task deleted successfully")
