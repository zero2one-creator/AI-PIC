from __future__ import annotations

import secrets
import time

from fastapi import APIRouter, Query
from sqlmodel import func, select

from app.api.deps import CurrentUser, SessionDep
from app.api.errors import AppError
from app.api.schemas import ApiEnvelope, OrderCreateRequest, OrderData, OrdersData
from app.models import Order, OrderStatus

router = APIRouter(prefix="/order", tags=["order"])


def _to_order_data(order: Order) -> OrderData:
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
    now = int(time.time())
    nonce = secrets.token_hex(6)
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
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ApiEnvelope:
    offset = (page - 1) * page_size

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
    order = session.exec(
        select(Order).where(Order.order_no == order_no, Order.user_id == current_user.id)
    ).first()
    if not order:
        raise AppError(code=404201, message="Order not found", status_code=404)
    return ApiEnvelope(data=_to_order_data(order))
