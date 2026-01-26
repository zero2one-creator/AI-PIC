"""
订阅路由模块

处理订阅相关的 API 端点，包括：
- 查询订阅状态（VIP 状态）
- RevenueCat Webhook 回调（处理 iOS/Android 订阅事件）

RevenueCat 是一个订阅管理平台，用于处理移动应用的订阅支付。
当用户在 iOS/Android 应用中购买订阅时，RevenueCat 会发送 webhook 事件到此端点。
"""
from __future__ import annotations

from datetime import datetime, timezone  # 日期时间处理
from decimal import Decimal  # 精确数值类型（用于金额）
from typing import Any  # 任意类型

from fastapi import APIRouter, Header  # FastAPI 路由和请求头
from sqlalchemy.exc import IntegrityError  # 数据库完整性错误
from sqlmodel import select  # SQLModel 查询

from app import crud  # 数据库操作
from app.api.deps import CurrentUser, SessionDep  # 依赖注入
from app.api.errors import AppError  # 自定义异常
from app.api.schemas import ApiEnvelope, SubscriptionStatusData
from app.core.config import settings  # 配置
from app.enums import (
    OrderStatus,  # 订单状态枚举
    PointTransactionType,  # 积分交易类型枚举
    ProductType,  # 产品类型枚举
    SubscriptionStatus,  # 订阅状态枚举
    VipType,
)
from app.models import (
    Order,
    RevenueCatEvent,
    Subscription,
    User,
)
from app.services.config_service import get_config  # 配置服务

router = APIRouter(prefix="/subscription", tags=["subscription"])


@router.get("/status", response_model=ApiEnvelope)
def status(current_user: CurrentUser) -> ApiEnvelope:
    """
    获取订阅状态

    返回当前登录用户的 VIP 订阅状态。

    请求路径: GET /api/v1/subscription/status

    Args:
        current_user: 当前登录用户

    Returns:
        ApiEnvelope: 包含订阅状态的响应
    """
    return ApiEnvelope(
        data=SubscriptionStatusData(
            is_vip=current_user.is_vip,
            vip_type=current_user.vip_type,
            vip_expire_time=current_user.vip_expire_time,
        )
    )


def _parse_ms(ms: Any) -> datetime | None:
    """
    将毫秒时间戳转换为 UTC 日期时间

    Args:
        ms: 毫秒时间戳（可以是整数或字符串）

    Returns:
        datetime | None: UTC 日期时间对象，如果解析失败则返回 None
    """
    if ms is None:
        return None
    try:
        ms_int = int(ms)
    except Exception:
        return None
    # 将毫秒转换为秒，然后转换为 UTC 时间
    return datetime.fromtimestamp(ms_int / 1000, tz=timezone.utc)


def _vip_type_for_product(product_id: str, cfg: dict[str, Any]) -> VipType | None:
    """
    根据产品 ID 确定 VIP 类型

    首先从配置中查找，如果找不到则使用启发式方法（根据产品 ID 名称判断）。

    Args:
        product_id: 产品 ID
        cfg: 配置字典

    Returns:
        VipType | None: VIP 类型，如果无法确定则返回 None
    """
    # 从配置中获取 VIP 产品配置
    vip_cfg = cfg.get("vip_products", {}) if isinstance(cfg, dict) else {}
    if isinstance(vip_cfg, dict):
        v = vip_cfg.get(product_id)
        if isinstance(v, str):
            if v.lower() == "weekly":
                return VipType.weekly
            if v.lower() == "lifetime":
                return VipType.lifetime

    # 回退启发式方法：根据产品 ID 名称判断
    pid = product_id.lower()
    if "life" in pid:
        return VipType.lifetime
    if "week" in pid:
        return VipType.weekly
    return None


def _points_pack_amount(product_id: str, cfg: dict[str, Any]) -> int | None:
    """
    根据产品 ID 获取积分包数量

    Args:
        product_id: 产品 ID
        cfg: 配置字典

    Returns:
        int | None: 积分数量，如果不是积分包则返回 None
    """
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
    """
    RevenueCat Webhook 回调端点

    处理来自 RevenueCat 的订阅事件，包括：
    - 订阅购买/续费
    - 订阅取消/过期
    - 积分包购买

    支持幂等性：通过 event_id 去重，防止重复处理同一事件。

    请求路径: POST /api/v1/subscription/webhook

    Args:
        session: 数据库会话
        payload: RevenueCat webhook 数据
        authorization: 授权头（用于验证 webhook 来源）

    Returns:
        ApiEnvelope: 接收确认响应

    Raises:
        AppError: 当授权失败、数据格式错误或处理失败时
    """
    secret = settings.REVENUECAT_WEBHOOK_SECRET
    if secret:
        # RevenueCat 允许配置任意 Authorization 头值
        # 接受原始密钥或 Bearer token 格式
        if authorization not in (secret, f"Bearer {secret}"):
            raise AppError(code=401001, message="Unauthorized", status_code=401)

    # 提取事件数据
    event = payload.get("event") if isinstance(payload, dict) else None
    if not isinstance(event, dict):
        raise AppError(code=400001, message="Invalid webhook payload", status_code=400)

    event_id = str(event.get("id") or "")
    event_type = str(event.get("type") or "")
    if not event_id or not event_type:
        raise AppError(code=400002, message="Missing event id/type", status_code=400)

    # 幂等性处理：RevenueCat 重试时使用相同的 event.id
    # 通过唯一约束防止重复处理
    try:
        session.add(RevenueCatEvent(event_id=event_id, event_type=event_type, payload=payload))
        session.flush()  # 刷新以触发唯一约束检查
    except IntegrityError:
        # 事件已处理过（event_id 重复），直接返回成功
        session.rollback()
        return ApiEnvelope(data={"received": True, "duplicate": True})

    # 测试事件：不做任何处理，直接返回成功
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

    # 处理积分包/消耗品购买
    if points_amount is not None and points_amount > 0:
        if not transaction_id:
            # 仍然记录事件，但无法安全地按交易去重
            session.rollback()
            raise AppError(code=400006, message="Missing transaction_id", status_code=400)

        # 检查订单是否已存在（防止重复处理）
        existing = session.exec(select(Order).where(Order.order_no == transaction_id)).first()
        if existing:
            # 订单已存在，直接返回成功（幂等性）
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

        # 发放积分（通过 event_id + order_no 唯一性保证幂等性）
        crud.change_points(
            session=session,
            user_id=user_id,
            delta=points_amount,
            tx_type=PointTransactionType.purchase,
            order_no=transaction_id,
        )
        return ApiEnvelope(data={"received": True})

    # 处理 VIP 产品（周订阅/终身会员），通过订阅或非续费购买
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
            # 确定是否应该授予 VIP 访问权限：
            # - 激活的订阅：VIP 直到过期时间（终身会员为 None 则永久）
            # - 已取消的订阅：VIP 直到过期时间
            # - 已过期的订阅：无 VIP 访问权限
            if sub.status == SubscriptionStatus.expired:
                is_vip = False
            elif expiration_at is None:
                # 终身订阅，没有过期日期
                is_vip = True
            else:
                # 有过期日期：如果尚未过期则为 VIP
                is_vip = expiration_at > now

            user.is_vip = is_vip
            user.vip_type = vip_type if is_vip else None
            user.vip_expire_time = expiration_at
            user.updated_at = now
            session.add(user)
            session.commit()

        return ApiEnvelope(data={"received": True})

    # 未知产品：只接受 webhook，不做处理
    session.commit()
    return ApiEnvelope(data={"received": True})
