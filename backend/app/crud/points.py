"""积分 CRUD 操作"""
from sqlmodel import Session, select

from app.api.errors import AppError
from app.enums import PointTransactionType
from app.models import PointTransaction, UserPoints, utc_now


def get_user_points(*, session: Session, user_id: int, for_update: bool = False) -> UserPoints:
    """获取用户积分账户，不存在则创建"""
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
    """变更用户积分并记录交易历史"""
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
