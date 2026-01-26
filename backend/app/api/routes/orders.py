"""
订单路由模块

处理订单相关的 API 端点，包括：
- 创建订单
- 查询订单列表（分页）
- 查询单个订单详情

订单用于记录用户购买积分包或订阅的交易信息。
"""
from __future__ import annotations

import secrets  # 生成随机字符串
import time  # 时间处理

from fastapi import APIRouter, Query  # FastAPI 路由和查询参数
from sqlmodel import func, select  # SQLModel 查询函数

from app.api.deps import CurrentUser, SessionDep  # 依赖注入
from app.api.errors import AppError  # 自定义异常
from app.api.schemas import ApiEnvelope, OrderCreateRequest, OrderData, OrdersData
from app.enums import OrderStatus  # 订单状态枚举
from app.models import Order  # 订单模型

router = APIRouter(prefix="/order", tags=["order"])


def _to_order_data(order: Order) -> OrderData:
    """
    将订单模型转换为响应数据模型

    Args:
        order: 订单数据库模型

    Returns:
        OrderData: 订单响应数据模型
    """
    return OrderData(
        order_no=order.order_no,
        product_type=order.product_type,
        product_id=order.product_id,
        quantity=order.quantity,
        amount=order.amount,
        currency=order.currency,
        status=order.status,
        created_at=order.created_at,
    )


@router.post("/create", response_model=ApiEnvelope)
def create_order(session: SessionDep, current_user: CurrentUser, body: OrderCreateRequest) -> ApiEnvelope:
    """
    创建订单

    生成唯一的订单号并创建订单记录。
    订单号格式：o_{user_id}_{timestamp}_{random}

    请求路径: POST /api/v1/order/create

    Args:
        session: 数据库会话
        current_user: 当前登录用户
        body: 订单创建请求数据

    Returns:
        ApiEnvelope: 包含订单信息的响应
    """
    now = int(time.time())  # 当前时间戳
    nonce = secrets.token_hex(6)  # 随机字符串（12 个字符）
    # 生成唯一订单号：o_用户ID_时间戳_随机字符串
    order_no = f"o_{current_user.id}_{now}_{nonce}"

    order = Order(
        user_id=current_user.id,
        order_no=order_no,
        product_type=body.product_type,
        product_id=body.product_id,
        quantity=body.quantity,
        amount=body.amount,
        currency=body.currency,
        status=OrderStatus.pending,
        payment_channel=None,
        transaction_id=None,
    )
    session.add(order)
    session.commit()
    session.refresh(order)
    return ApiEnvelope(data=_to_order_data(order))


@router.get("/list", response_model=ApiEnvelope)
def list_orders(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),  # 页码，从 1 开始
    page_size: int = Query(default=20, ge=1, le=100),  # 每页数量，1-100
) -> ApiEnvelope:
    """
    获取订单列表（分页）

    查询当前用户的所有订单，按创建时间倒序排列。

    请求路径: GET /api/v1/order/list?page=1&page_size=20

    Args:
        session: 数据库会话
        current_user: 当前登录用户
        page: 页码（从 1 开始）
        page_size: 每页数量（1-100）

    Returns:
        ApiEnvelope: 包含订单列表和总数的响应
    """
    offset = (page - 1) * page_size  # 计算偏移量

    count_stmt = (
        select(func.count())
        .select_from(Order)
        .where(Order.user_id == current_user.id)
    )
    count = session.exec(count_stmt).one()

    stmt = (
        select(Order)
        .where(Order.user_id == current_user.id)
        .order_by(Order.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    rows = session.exec(stmt).all()
    data = [_to_order_data(o) for o in rows]
    return ApiEnvelope(data=OrdersData(data=data, count=count))


@router.get("/{order_no}", response_model=ApiEnvelope)
def get_order(session: SessionDep, current_user: CurrentUser, order_no: str) -> ApiEnvelope:
    """
    获取订单详情

    根据订单号查询订单信息，只能查询当前用户自己的订单。

    请求路径: GET /api/v1/order/{order_no}

    Args:
        session: 数据库会话
        current_user: 当前登录用户
        order_no: 订单号

    Returns:
        ApiEnvelope: 包含订单详情的响应

    Raises:
        AppError: 当订单不存在或不属于当前用户时抛出 404201 错误
    """
    order = session.exec(
        select(Order).where(Order.order_no == order_no, Order.user_id == current_user.id)
    ).first()
    if not order:
        raise AppError(code=404201, message="Order not found", status_code=404)
    return ApiEnvelope(data=_to_order_data(order))
