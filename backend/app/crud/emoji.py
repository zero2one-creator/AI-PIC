"""表情任务 CRUD 操作"""
from sqlmodel import Session

from app.enums import EmojiTaskStatus
from app.models import EmojiTask


def create_task(
    *,
    session: Session,
    user_id: int,
    image_url: str,
    driven_id: str,
    detect_result: dict | None,
    points_cost: int,
    style_name: str | None = None,
) -> EmojiTask:
    """创建表情生成任务"""
    task = EmojiTask(
        user_id=user_id,
        driven_id=driven_id,
        style_name=style_name,
        source_image_url=image_url,
        detect_result=detect_result,
        status=EmojiTaskStatus.pending,
        points_cost=points_cost,
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    return task
