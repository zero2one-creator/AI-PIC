"""
表情生成路由模块

处理表情生成相关的 API 端点，包括：
- 上传图片并检测人脸
- 创建表情生成任务（扣除积分，异步处理）
- 查询表情生成历史（分页）
"""
from __future__ import annotations

import json
import secrets
import time
from io import BytesIO

from fastapi import APIRouter, Query, UploadFile
from sqlmodel import func, select

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.api.errors import AppError
from app.api.schemas import (
    ApiEnvelope,
    EmojiCreateRequest,
    EmojiDetectData,
    EmojiHistoryData,
    EmojiTaskData,
)
from app.core.config import settings
from app.core.redis import get_redis
from app.enums import EmojiTaskStatus, PointTransactionType
from app.integrations.aliyun_emoji import aliyun_emoji_client
from app.integrations.oss import upload_file
from app.models import EmojiTask, utc_now
from app.services.config_service import get_config

router = APIRouter(prefix="/emoji", tags=["emoji"])

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("/detect", response_model=ApiEnvelope)
async def detect(current_user: CurrentUser, file: UploadFile) -> ApiEnvelope:
    """
    上传图片并检测人脸

    接收图片文件，上传到 OSS，然后调用阿里云 API 检测人脸。

    请求路径: POST /api/v1/emoji/detect
    Content-Type: multipart/form-data

    Args:
        current_user: 当前登录用户
        file: 上传的图片文件

    Returns:
        ApiEnvelope: 包含图片 URL 和检测结果
    """
    # 验证文件类型
    if not file.filename:
        raise AppError(code=400001, message="No filename", status_code=400)
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise AppError(code=400002, message="Invalid file type", status_code=400)

    # 验证文件大小
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise AppError(code=400003, message="File too large", status_code=400)

    # 生成 OSS key 并上传
    ts = int(time.time())
    rand = secrets.token_hex(8)
    key = f"{settings.OSS_DIR_PREFIX}/{current_user.id}/{ts}_{rand}.{ext}"

    image_url = upload_file(file=BytesIO(content), key=key, content_type=file.content_type)

    # 检测人脸
    r = aliyun_emoji_client.detect(image_url=image_url)

    return ApiEnvelope(
        data=EmojiDetectData(
            image_url=image_url,
            passed=r.passed,
            face_bbox=r.face_bbox,
            ext_bbox=r.ext_bbox,
            raw=r.raw,
        )
    )


@router.post("/create", response_model=ApiEnvelope)
def create(session: SessionDep, current_user: CurrentUser, body: EmojiCreateRequest) -> ApiEnvelope:
    """
    创建表情生成任务

    创建表情生成任务，扣除积分，并将任务加入 Redis Streams 队列等待后台处理。
    如果用户没有提供人脸位置信息，会自动调用检测接口。

    重要：积分在任务创建时立即扣除，即使后续生成失败也不会退款。

    请求路径: POST /api/v1/emoji/create

    Args:
        session: 数据库会话
        current_user: 当前登录用户
        body: 创建请求数据（图片 URL、驱动图片 ID 等）

    Returns:
        ApiEnvelope: 包含任务信息的响应

    Raises:
        AppError: 当积分不足、图片检测失败或 Redis 队列不可用时
    """
    cfg = get_config()
    # 从配置获取表情生成消耗的积分（默认 200）
    points_cost = int(cfg.get("points_rules", {}).get("emoji", 200))

    # 获取人脸位置信息（如果用户没有提供，则自动检测）
    face_bbox = body.face_bbox
    ext_bbox = body.ext_bbox
    raw_detect = None
    if not face_bbox or not ext_bbox:
        # 用户没有提供位置信息，自动调用检测接口
        detect_r = aliyun_emoji_client.detect(image_url=body.image_url)
        if not detect_r.passed or not detect_r.face_bbox or not detect_r.ext_bbox:
            # 检测失败，抛出错误
            raise AppError(
                code=400101,
                message=detect_r.error_message or "Image detect failed",
                status_code=400,
            )
        face_bbox = detect_r.face_bbox
        ext_bbox = detect_r.ext_bbox
        raw_detect = detect_r.raw

    # 构建检测结果
    detect_result = {"face_bbox": face_bbox, "ext_bbox": ext_bbox, "raw": raw_detect}

    # 先扣除积分（确认：即使生成失败，积分也不会退款）
    crud.change_points(
        session=session,
        user_id=current_user.id,
        delta=-points_cost,  # 负数表示扣除
        tx_type=PointTransactionType.consume,
        task_type="emoji",
    )

    # 创建表情生成任务
    task = crud.create_emoji_task(
        session=session,
        user_id=current_user.id,
        image_url=body.image_url,
        driven_id=body.driven_id,
        detect_result=detect_result,
        points_cost=points_cost,
    )

    # 将任务加入 Redis Streams 队列，等待后台 worker 异步处理
    redis_enqueue_failed = False
    redis_error_msg = ""
    try:
        rds = get_redis()
        # 使用 Redis Streams 的 XADD 命令添加任务
        rds.xadd(
            "emoji_tasks",  # Stream 名称
            {
                "task_id": str(task.id),
                "user_id": str(current_user.id),
                "image_url": body.image_url,
                "driven_id": body.driven_id,
                "detect_result": json.dumps(detect_result),  # JSON 序列化
            },
        )
    except Exception as e:
        # Redis 队列不可用，标记失败，稍后更新任务状态
        redis_enqueue_failed = True
        redis_error_msg = f"Queue unavailable: {e}"

    # 如果 Redis 入队失败，在单独的事务中更新任务状态为失败
    if redis_enqueue_failed:
        task.status = EmojiTaskStatus.failed
        task.error_message = redis_error_msg
        task.completed_at = utc_now()
        session.add(task)
        session.commit()
        session.refresh(task)

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
    """
    查询任务状态

    查询指定表情生成任务的状态和结果。

    请求路径: GET /api/v1/emoji/task/{task_id}

    Args:
        session: 数据库会话
        current_user: 当前登录用户
        task_id: 任务 ID

    Returns:
        ApiEnvelope: 包含任务信息的响应

    Raises:
        AppError: 当任务不存在或不属于当前用户时抛出 404101 错误
    """
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
    page: int = Query(default=1, ge=1),  # 页码，从 1 开始
    page_size: int = Query(default=20, ge=1, le=100),  # 每页数量，1-100
) -> ApiEnvelope:
    """
    获取表情生成历史（分页）

    查询当前登录用户的所有表情生成任务，按创建时间倒序排列。

    请求路径: GET /api/v1/emoji/history?page=1&page_size=20

    Args:
        session: 数据库会话
        current_user: 当前登录用户
        page: 页码（从 1 开始）
        page_size: 每页数量（1-100）

    Returns:
        ApiEnvelope: 包含任务列表和总数的响应
    """
    offset = (page - 1) * page_size  # 计算偏移量

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
    """
    删除任务

    删除指定的表情生成任务。只能删除自己的任务。

    请求路径: DELETE /api/v1/emoji/task/{task_id}

    Args:
        session: 数据库会话
        current_user: 当前登录用户
        task_id: 任务 ID

    Returns:
        ApiEnvelope: 删除成功的响应

    Raises:
        AppError: 当任务不存在或不属于当前用户时抛出 404101 错误
    """
    task = session.get(EmojiTask, task_id)
    if not task or task.user_id != current_user.id:
        raise AppError(code=404101, message="Task not found", status_code=404)
    session.delete(task)
    session.commit()
    return ApiEnvelope(data={"deleted": True})
