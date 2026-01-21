"""
订阅管理 API 路由
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Request

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.models import Message, SubscriptionCreate, SubscriptionPublic, SubscriptionUpdate
from app.services.revenuecat_service import get_revenuecat_service

router = APIRouter(prefix="/subscription", tags=["subscription"])


@router.get("/status", response_model=SubscriptionPublic | None)
def get_subscription_status(
    session: SessionDep,
    current_user: CurrentUser,
) -> SubscriptionPublic | None:
    """
    查询用户订阅状态
    """
    subscription = crud.get_user_active_subscription(session=session, user_id=current_user.id)
    return subscription


@router.post("/webhook")
async def revenuecat_webhook(request: Request, session: SessionDep) -> Message:
    """
    RevenueCat Webhook 回调

    处理订阅事件:
    - INITIAL_PURCHASE: 首次购买
    - RENEWAL: 续费
    - CANCELLATION: 取消订阅
    - EXPIRATION: 订阅过期
    - PRODUCT_CHANGE: 变更套餐
    """
    try:
        # 获取原始请求体
        body = await request.body()

        # 验证签名
        signature = request.headers.get("X-RevenueCat-Signature", "")
        rc_service = get_revenuecat_service()

        if not rc_service.verify_webhook_signature(body, signature):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

        # 解析事件
        event_data = await request.json()
        parsed_event = rc_service.parse_webhook_event(event_data)

        event_type = parsed_event.get("event_type")
        app_user_id = parsed_event.get("app_user_id")

        if not app_user_id:
            raise HTTPException(status_code=400, detail="Missing app_user_id")

        # 查询用户(假设 app_user_id 就是我们的 user_id)
        try:
            user_id = int(app_user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid app_user_id format")

        user = crud.get_user_by_id(session=session, user_id=user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # 处理不同的事件类型
        if event_type in ["INITIAL_PURCHASE", "RENEWAL"]:
            # 首次购买或续费
            await _handle_purchase_event(session, user_id, parsed_event)

        elif event_type == "CANCELLATION":
            # 取消订阅(保留至到期日)
            await _handle_cancellation_event(session, user_id, parsed_event)

        elif event_type == "EXPIRATION":
            # 订阅过期
            await _handle_expiration_event(session, user_id, parsed_event)

        elif event_type == "PRODUCT_CHANGE":
            # 变更套餐
            await _handle_product_change_event(session, user_id, parsed_event)

        return Message(message="Webhook processed successfully")

    except HTTPException:
        raise
    except Exception as e:
        import logging

        logging.error(f"Webhook processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")


async def _handle_purchase_event(session: SessionDep, user_id: int, event: dict) -> None:
    """处理购买/续费事件"""
    product_id = event.get("product_id")
    expiration_at = event.get("expiration_at")
    purchased_at = event.get("purchased_at")
    will_renew = event.get("will_renew", True)

    if not product_id:
        raise HTTPException(status_code=400, detail="Missing product_id in subscription event")

    # 判断订阅类型
    plan_type = "weekly" if "weekly" in product_id.lower() else "lifetime"

    # 查询现有订阅
    existing_sub = crud.get_user_active_subscription(session=session, user_id=user_id)

    if existing_sub:
        # 更新现有订阅
        sub_update = SubscriptionUpdate(
            status="active",
            will_renew=will_renew,
            current_period_end=expiration_at,
            cancelled_at=None,
        )
        crud.update_subscription(session=session, db_subscription=existing_sub, subscription_in=sub_update)
    else:
        # 创建新订阅
        sub_create = SubscriptionCreate(
            user_id=user_id,
            rc_subscriber_id=str(user_id),
            product_id=product_id,
            plan_type=plan_type,
            status="active",
            will_renew=will_renew,
            current_period_start=purchased_at or datetime.utcnow(),
            current_period_end=expiration_at or datetime.utcnow(),
        )
        crud.create_subscription(session=session, subscription_in=sub_create)

    # 更新用户会员状态
    user = crud.get_user_by_id(session=session, user_id=user_id)
    if user:
        from app.models import UserUpdate

        user_update = UserUpdate(
            is_vip=True,
            vip_type=plan_type,
            vip_expire_time=expiration_at,
        )
        crud.update_user(session=session, db_user=user, user_in=user_update)


async def _handle_cancellation_event(session: SessionDep, user_id: int, event: dict) -> None:
    """处理取消订阅事件"""
    subscription = crud.get_user_active_subscription(session=session, user_id=user_id)

    if subscription:
        sub_update = SubscriptionUpdate(
            status="cancelled",
            will_renew=False,
            cancelled_at=datetime.utcnow(),
        )
        crud.update_subscription(session=session, db_subscription=subscription, subscription_in=sub_update)


async def _handle_expiration_event(session: SessionDep, user_id: int, event: dict) -> None:
    """处理订阅过期事件"""
    subscription = crud.get_user_active_subscription(session=session, user_id=user_id)

    if subscription:
        sub_update = SubscriptionUpdate(
            status="expired",
            will_renew=False,
        )
        crud.update_subscription(session=session, db_subscription=subscription, subscription_in=sub_update)

    # 更新用户会员状态
    user = crud.get_user_by_id(session=session, user_id=user_id)
    if user:
        from app.models import UserUpdate

        user_update = UserUpdate(
            is_vip=False,
            vip_type=None,
            vip_expire_time=None,
        )
        crud.update_user(session=session, db_user=user, user_in=user_update)


async def _handle_product_change_event(session: SessionDep, user_id: int, event: dict) -> None:
    """处理套餐变更事件"""
    # 类似购买事件处理
    await _handle_purchase_event(session, user_id, event)
