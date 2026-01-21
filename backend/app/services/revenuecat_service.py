"""
RevenueCat 订阅管理服务

文档: https://www.revenuecat.com/docs/welcome/overview
Webhook: https://www.revenuecat.com/docs/integrations/webhooks
"""

import hashlib
import hmac
import logging
from datetime import datetime
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class RevenueCatService:
    """RevenueCat 服务封装"""

    def __init__(self, api_key: str, webhook_secret: str | None = None):
        """
        初始化 RevenueCat 服务

        Args:
            api_key: RevenueCat API Key
            webhook_secret: Webhook 签名密钥
        """
        self.api_key = api_key
        self.webhook_secret = webhook_secret
        self.base_url = "https://api.revenuecat.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        logger.info("RevenueCat service initialized")

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        验证 Webhook 签名

        Args:
            payload: 请求体原始字节
            signature: X-RevenueCat-Signature 头部值

        Returns:
            是否验证通过
        """
        if not self.webhook_secret:
            logger.warning("Webhook secret not configured, skipping signature verification")
            return True

        try:
            expected_signature = hmac.new(
                self.webhook_secret.encode(),
                payload,
                hashlib.sha256,
            ).hexdigest()

            return hmac.compare_digest(signature, expected_signature)
        except Exception as e:
            logger.error(f"Failed to verify webhook signature: {e}")
            return False

    async def get_subscriber_info(self, app_user_id: str) -> dict[str, Any]:
        """
        获取订阅者信息

        Args:
            app_user_id: 应用用户 ID

        Returns:
            订阅者信息
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/subscribers/{app_user_id}",
                    headers=self.headers,
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Get subscriber info error: {response.status_code} {response.text}")
                    return {}
        except Exception as e:
            logger.error(f"Failed to get subscriber info: {e}")
            return {}

    def parse_webhook_event(self, event_data: dict[str, Any]) -> dict[str, Any]:
        """
        解析 Webhook 事件

        Args:
            event_data: Webhook 事件数据

        Returns:
            {
                "event_type": str,  # INITIAL_PURCHASE, RENEWAL, CANCELLATION, etc.
                "app_user_id": str,
                "product_id": str,
                "period_type": str,  # NORMAL, TRIAL, INTRO
                "purchased_at": datetime,
                "expiration_at": datetime,
                "is_trial": bool,
                "will_renew": bool,
                "subscriber_attributes": dict,
            }
        """
        try:
            event = event_data.get("event", {})
            event_type = event.get("type")
            app_user_id = event.get("app_user_id")

            # 获取订阅信息
            subscriber = event_data.get("subscriber", {})
            entitlements = subscriber.get("entitlements", {})
            subscriptions = subscriber.get("subscriptions", {})

            # 获取第一个活跃订阅
            active_subscription = None
            for sub_id, sub_data in subscriptions.items():
                if sub_data.get("is_active"):
                    active_subscription = sub_data
                    break

            if not active_subscription and subscriptions:
                # 如果没有活跃订阅,取最新的
                active_subscription = list(subscriptions.values())[0]

            result = {
                "event_type": event_type,
                "app_user_id": app_user_id,
                "product_id": active_subscription.get("product_id") if active_subscription else None,
                "period_type": active_subscription.get("period_type") if active_subscription else None,
                "purchased_at": self._parse_datetime(
                    active_subscription.get("purchase_date") if active_subscription else None
                ),
                "expiration_at": self._parse_datetime(
                    active_subscription.get("expires_date") if active_subscription else None
                ),
                "is_trial": active_subscription.get("is_trial_period", False) if active_subscription else False,
                "will_renew": active_subscription.get("will_renew", False) if active_subscription else False,
                "subscriber_attributes": subscriber.get("subscriber_attributes", {}),
            }

            return result
        except Exception as e:
            logger.error(f"Failed to parse webhook event: {e}")
            return {}

    def _parse_datetime(self, date_str: str | None) -> datetime | None:
        """解析 ISO 8601 日期时间字符串"""
        if not date_str:
            return None
        try:
            # RevenueCat 使用 ISO 8601 格式
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception as e:
            logger.error(f"Failed to parse datetime {date_str}: {e}")
            return None


# 全局 RevenueCat 服务实例
_revenuecat_service: RevenueCatService | None = None


def init_revenuecat_service(api_key: str, webhook_secret: str | None = None) -> RevenueCatService:
    """
    初始化全局 RevenueCat 服务

    Args:
        api_key: RevenueCat API Key
        webhook_secret: Webhook 签名密钥

    Returns:
        RevenueCat 服务实例
    """
    global _revenuecat_service
    _revenuecat_service = RevenueCatService(api_key=api_key, webhook_secret=webhook_secret)
    return _revenuecat_service


def get_revenuecat_service() -> RevenueCatService:
    """
    获取全局 RevenueCat 服务实例

    Returns:
        RevenueCat 服务实例

    Raises:
        RuntimeError: 如果服务未初始化
    """
    if _revenuecat_service is None:
        # 尝试从配置初始化
        if settings.REVENUECAT_API_KEY:
            return init_revenuecat_service(
                api_key=settings.REVENUECAT_API_KEY,
                webhook_secret=settings.REVENUECAT_WEBHOOK_SECRET,
            )
        raise RuntimeError("RevenueCat service not initialized and config not available.")
    return _revenuecat_service
