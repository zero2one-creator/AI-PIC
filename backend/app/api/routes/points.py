"""
积分路由模块

处理积分相关的 API 端点，包括：
- 查询积分余额
- 查询积分交易历史（分页）
"""
from __future__ import annotations

from fastapi import APIRouter, Query  # FastAPI 路由和查询参数
from sqlmodel import func, select  # SQLModel 查询函数

from app import crud  # 数据库操作
from app.api.deps import CurrentUser, SessionDep  # 依赖注入
from app.api.schemas import (
    ApiEnvelope,
    PointsBalanceData,
    PointsTransactionsData,
    PointTransactionPublic,
)
from app.models import PointTransaction  # 积分交易模型

router = APIRouter(prefix="/points", tags=["points"])


@router.get("/balance", response_model=ApiEnvelope)
def balance(session: SessionDep, current_user: CurrentUser) -> ApiEnvelope:
    """
    获取积分余额

    查询当前登录用户的积分余额。

    请求路径: GET /api/v1/points/balance

    Args:
        session: 数据库会话
        current_user: 当前登录用户

    Returns:
        ApiEnvelope: 包含积分余额的响应
    """
    points = crud.get_user_points(session=session, user_id=current_user.id)
    return ApiEnvelope(data=PointsBalanceData(balance=points.balance))


@router.get("/transactions", response_model=ApiEnvelope)
def transactions(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),  # 页码，从 1 开始
    page_size: int = Query(default=20, ge=1, le=100),  # 每页数量，1-100
) -> ApiEnvelope:
    """
    获取积分交易历史（分页）

    查询当前登录用户的所有积分变动记录，按时间倒序排列。

    请求路径: GET /api/v1/points/transactions?page=1&page_size=20

    Args:
        session: 数据库会话
        current_user: 当前登录用户
        page: 页码（从 1 开始）
        page_size: 每页数量（1-100）

    Returns:
        ApiEnvelope: 包含交易记录列表和总数的响应
    """
    offset = (page - 1) * page_size  # 计算偏移量

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

