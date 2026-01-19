"""
积分管理 API 路由
"""

from fastapi import APIRouter, HTTPException

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.models import PointTransactionPublic, PointTransactionsPublic, UserPointsPublic

router = APIRouter(prefix="/points", tags=["points"])


@router.get("/balance", response_model=UserPointsPublic)
def get_points_balance(session: SessionDep, current_user: CurrentUser) -> UserPointsPublic:
    """
    获取当前用户积分余额
    """
    user_points = crud.get_user_points(session=session, user_id=current_user.id)
    if not user_points:
        user_points = crud.init_user_points(session=session, user_id=current_user.id)
    return user_points


@router.get("/transactions", response_model=PointTransactionsPublic)
def get_point_transactions(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> PointTransactionsPublic:
    """
    获取积分流水记录
    """
    transactions = crud.get_point_transactions(
        session=session,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )
    return PointTransactionsPublic(
        data=transactions,
        count=len(transactions),
    )
