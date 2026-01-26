"""用户 CRUD 操作"""
from datetime import datetime

from sqlmodel import Session, select

from app.api.errors import AppError
from app.models import User, UserPoints, utc_now


def get_by_device_id(*, session: Session, device_id: str) -> User | None:
    """根据设备 ID 查询用户"""
    statement = select(User).where(User.device_id == device_id)
    return session.exec(statement).first()


def create(*, session: Session, device_id: str) -> User:
    """创建新用户，同时初始化积分账户"""
    user = User(device_id=device_id)
    session.add(user)
    session.flush()
    session.add(UserPoints(user_id=user.id, balance=0))
    session.commit()
    session.refresh(user)
    return user


def get_or_create_by_device_id(*, session: Session, device_id: str) -> User:
    """根据设备 ID 获取或创建用户"""
    user = get_by_device_id(session=session, device_id=device_id)
    if user:
        return user
    return create(session=session, device_id=device_id)


def update_vip(
    *,
    session: Session,
    user_id: int,
    is_vip: bool,
    vip_type: str | None,
    vip_expire_time: datetime | None,
) -> None:
    """更新用户 VIP 状态"""
    user = session.get(User, user_id)
    if not user:
        raise AppError(code=404001, message="User not found", status_code=404)
    user.is_vip = is_vip
    user.vip_type = vip_type  # type: ignore[assignment]
    user.vip_expire_time = vip_expire_time
    user.updated_at = utc_now()
    session.add(user)
    session.commit()
