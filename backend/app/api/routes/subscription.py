from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Header
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.api.errors import AppError
from app.api.schemas import ApiEnvelope, SubscriptionStatusData
from app.core.config import settings
from app.models import (
    Order,
    OrderStatus,
    PointTransactionType,
    ProductType,
    RevenueCatEvent,
    Subscription,
    SubscriptionStatus,
    User,
    VipType,
)
from app.services.config_service import get_config

router = APIRouter(prefix="/subscription", tags=["subscription"])


@router.get("/status", response_model=ApiEnvelope)
def status(current_user: CurrentUser) -> ApiEnvelope:
    return ApiEnvelope(
        data=SubscriptionStatusData(
            is_vip=current_user.is_vip,
            vip_type=current_user.vip_type,
            vip_expire_time=current_user.vip_expire_time,
        )
    )


def _parse_ms(ms: Any) -> datetime | None:
    if ms is None:
        return None
    try:
        ms_int = int(ms)
    except Exception:
        return None
    return datetime.fromtimestamp(ms_int / 1000, tz=timezone.utc)


def _vip_type_for_product(product_id: str, cfg: dict[str, Any]) -> VipType | None:
    vip_cfg = cfg.get("vip_products", {}) if isinstance(cfg, dict) else {}
    if isinstance(vip_cfg, dict):
        v = vip_cfg.get(product_id)
        if isinstance(v, str):
            if v.lower() == "weekly":
                return VipType.weekly
            if v.lower() == "lifetime":
                return VipType.lifetime

    # Fallback heuristic.
    pid = product_id.lower()
    if "life" in pid:
        return VipType.lifetime
    if "week" in pid:
        return VipType.weekly
    return None


def _points_pack_amount(product_id: str, cfg: dict[str, Any]) -> int | None:
    packs = cfg.get("points_packs", {}) if isinstance(cfg, dict) else {}
    if not isinstance(packs, dict):
        return None
    v = packs.get(product_id)
    try:
        return int(v) if v is not None else None
    except Exception:
        return None


@router.post("/webhook", response_model=ApiEnvelope)
def webhook(
    session: SessionDep,
    payload: dict[str, Any],
    authorization: str | None = Header(default=None),
) -> ApiEnvelope:
    secret = settings.REVENUECAT_WEBHOOK_SECRET
    if secret:
        # RevenueCat allows configuring an arbitrary Authorization header value.
        # Accept either the raw secret or a Bearer token with that secret.
        if authorization not in (secret, f"Bearer {secret}"):
            raise AppError(code=401001, message="Unauthorized", status_code=401)

    event = payload.get("event") if isinstance(payload, dict) else None
    if not isinstance(event, dict):
        raise AppError(code=400001, message="Invalid webhook payload", status_code=400)

    event_id = str(event.get("id") or "")
    event_type = str(event.get("type") or "")
    if not event_id or not event_type:
        raise AppError(code=400002, message="Missing event id/type", status_code=400)

    # Idempotency: RevenueCat retries use the same event.id
    try:
        session.add(RevenueCatEvent(event_id=event_id, event_type=event_type, payload=payload))
        session.flush()
    except IntegrityError:
        session.rollback()
        return ApiEnvelope(data={"received": True, "duplicate": True})

    # No-op test event.
    if event_type.upper() == "TEST":
        session.commit()
        return ApiEnvelope(data={"received": True})

    app_user_id = event.get("app_user_id")
    if app_user_id is None:
        raise AppError(code=400003, message="Missing app_user_id", status_code=400)
    try:
        user_id = int(str(app_user_id))
    except ValueError:
        raise AppError(code=400004, message="Invalid app_user_id", status_code=400)

    product_id = str(event.get("product_id") or "")
    if not product_id:
        raise AppError(code=400005, message="Missing product_id", status_code=400)

    cfg = get_config()
    vip_type = _vip_type_for_product(product_id, cfg)
    points_amount = _points_pack_amount(product_id, cfg)

    purchased_at = _parse_ms(event.get("purchased_at_ms"))
    expiration_at = _parse_ms(event.get("expiration_at_ms"))
    transaction_id = str(event.get("transaction_id") or "")

    price = event.get("price")
    currency = str(event.get("currency") or "USD")
    amount = Decimal(str(price)) if price is not None else Decimal("0.00")

    # Points pack / consumable purchase
    if points_amount is not None and points_amount > 0:
        if not transaction_id:
            # Still record the event but can't safely dedupe per transaction.
            session.rollback()
            raise AppError(code=400006, message="Missing transaction_id", status_code=400)

        existing = session.exec(select(Order).where(Order.order_no == transaction_id)).first()
        if existing:
            session.commit()
            return ApiEnvelope(data={"received": True})

        order = Order(
            user_id=user_id,
            order_no=transaction_id,
            product_type=ProductType.points_pack,
            product_id=product_id,
            quantity=1,
            amount=amount,
            currency=currency,
            status=OrderStatus.paid,
            payment_channel="revenuecat",
            transaction_id=transaction_id,
        )
        session.add(order)
        session.commit()

        # Grant points (idempotent via event_id + order_no unique).
        crud.change_points(
            session=session,
            user_id=user_id,
            delta=points_amount,
            tx_type=PointTransactionType.purchase,
            order_no=transaction_id,
        )
        return ApiEnvelope(data={"received": True})

    # VIP product (weekly/lifetime) via subscription or non-renewing purchase.
    if vip_type is not None:
        sub = session.exec(
            select(Subscription).where(
                Subscription.user_id == user_id, Subscription.product_id == product_id
            )
        ).first()

        now = datetime.now(timezone.utc)
        if not sub:
            sub = Subscription(
                user_id=user_id,
                rc_subscriber_id=str(event.get("original_app_user_id") or ""),
                product_id=product_id,
                plan_type=vip_type,
                status=SubscriptionStatus.active,
                will_renew=True,
                current_period_start=purchased_at,
                current_period_end=expiration_at,
            )
        sub.plan_type = vip_type
        sub.current_period_start = purchased_at or sub.current_period_start
        sub.current_period_end = expiration_at or sub.current_period_end
        sub.updated_at = now

        et = event_type.upper()
        if et in ("CANCELLATION", "BILLING_ISSUE", "SUBSCRIPTION_PAUSED"):
            sub.status = SubscriptionStatus.cancelled
            sub.will_renew = False
            sub.cancelled_at = now
        elif et in ("EXPIRATION", "SUBSCRIPTION_EXPIRED"):
            sub.status = SubscriptionStatus.expired
            sub.will_renew = False
        else:
            sub.status = SubscriptionStatus.active
            sub.will_renew = True

        session.add(sub)
        session.commit()

        user = session.get(User, user_id)
        if user:
            # Determine if VIP access should be granted:
            # - Active subscription: VIP until expiration_at (or forever if None for lifetime)
            # - Cancelled subscription: VIP until expiration_at
            # - Expired subscription: No VIP access
            if sub.status == SubscriptionStatus.expired:
                is_vip = False
            elif expiration_at is None:
                # Lifetime subscription with no expiration date
                is_vip = True
            else:
                # Has expiration date: VIP if not yet expired
                is_vip = expiration_at > now

            user.is_vip = is_vip
            user.vip_type = vip_type if is_vip else None
            user.vip_expire_time = expiration_at
            user.updated_at = now
            session.add(user)
            session.commit()

        return ApiEnvelope(data={"received": True})

    # Unknown product: just accept webhook.
    session.commit()
    return ApiEnvelope(data={"received": True})
