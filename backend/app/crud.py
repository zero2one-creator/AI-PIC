from __future__ import annotations

from datetime import datetime

from sqlmodel import Session, select

from app.api.errors import AppError
from app.models import (
    EmojiTask,
    EmojiTaskStatus,
    PointTransaction,
    PointTransactionType,
    User,
    UserPoints,
    utc_now,
)


def get_user_by_device_id(*, session: Session, device_id: str) -> User | None:
    statement = select(User).where(User.device_id == device_id)
    return session.exec(statement).first()


def create_user(*, session: Session, device_id: str) -> User:
    user = User(device_id=device_id)
    session.add(user)
    session.flush()
    # Ensure a points row exists.
    session.add(UserPoints(user_id=user.id, balance=0))
    session.commit()
    session.refresh(user)
    return user


def get_or_create_user_by_device_id(*, session: Session, device_id: str) -> User:
    user = get_user_by_device_id(session=session, device_id=device_id)
    if user:
        return user
    return create_user(session=session, device_id=device_id)


def get_user_points(*, session: Session, user_id: int, for_update: bool = False) -> UserPoints:
    stmt = select(UserPoints).where(UserPoints.user_id == user_id)
    if for_update:
        stmt = stmt.with_for_update()
    points = session.exec(stmt).first()
    if not points:
        points = UserPoints(user_id=user_id, balance=0)
        session.add(points)
        session.commit()
        session.refresh(points)
    return points


def change_points(
    *,
    session: Session,
    user_id: int,
    delta: int,
    tx_type: PointTransactionType,
    task_type: str | None = None,
    order_no: str | None = None,
    reward_week: str | None = None,
) -> UserPoints:
    points = get_user_points(session=session, user_id=user_id, for_update=True)
    new_balance = points.balance + delta
    if new_balance < 0:
        raise AppError(code=402001, message="Insufficient points", status_code=400)

    points.balance = new_balance
    points.updated_at = utc_now()

    tx = PointTransaction(
        user_id=user_id,
        type=tx_type,
        amount=delta,
        balance_after=new_balance,
        task_type=task_type,
        order_no=order_no,
        reward_week=reward_week,
    )

    session.add(points)
    session.add(tx)
    session.commit()
    session.refresh(points)
    return points


def create_emoji_task(
    *,
    session: Session,
    user_id: int,
    image_url: str,
    driven_id: str,
    detect_result: dict | None,
    points_cost: int,
    style_name: str | None = None,
) -> EmojiTask:
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


def update_user_vip(
    *,
    session: Session,
    user_id: int,
    is_vip: bool,
    vip_type: str | None,
    vip_expire_time: datetime | None,
) -> None:
    user = session.get(User, user_id)
    if not user:
        raise AppError(code=404001, message="User not found", status_code=404)
    user.is_vip = is_vip
    user.vip_type = vip_type  # type: ignore[assignment]
    user.vip_expire_time = vip_expire_time
    user.updated_at = utc_now()
    session.add(user)
    session.commit()

