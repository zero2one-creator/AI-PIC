from __future__ import annotations

from fastapi import APIRouter, Query
from sqlmodel import func, select

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.api.schemas import (
    ApiEnvelope,
    PointsBalanceData,
    PointsTransactionsData,
    PointTransactionPublic,
)
from app.models import PointTransaction

router = APIRouter(prefix="/points", tags=["points"])


@router.get("/balance", response_model=ApiEnvelope)
def balance(session: SessionDep, current_user: CurrentUser) -> ApiEnvelope:
    points = crud.get_user_points(session=session, user_id=current_user.id)
    return ApiEnvelope(data=PointsBalanceData(balance=points.balance))


@router.get("/transactions", response_model=ApiEnvelope)
def transactions(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ApiEnvelope:
    offset = (page - 1) * page_size

    count_stmt = (
        select(func.count())
        .select_from(PointTransaction)
        .where(PointTransaction.user_id == current_user.id)
    )
    count = session.exec(count_stmt).one()

    stmt = (
        select(PointTransaction)
        .where(PointTransaction.user_id == current_user.id)
        .order_by(PointTransaction.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    rows = session.exec(stmt).all()

    data = [
        PointTransactionPublic(
            id=row.id,
            type=row.type,
            amount=row.amount,
            balance_after=row.balance_after,
            task_type=row.task_type,
            order_no=row.order_no,
            reward_week=row.reward_week,
            created_at=row.created_at,
        )
        for row in rows
    ]
    return ApiEnvelope(data=PointsTransactionsData(data=data, count=count))

