"""
数据库模型定义模块

本模块使用 SQLModel 定义所有数据库表结构。

模型按功能拆分：
- user.py: 用户模型
- points.py: 积分相关模型
- subscription.py: 订阅模型
- order.py: 订单模型
- emoji.py: 表情生成任务模型
- revenuecat.py: RevenueCat 事件模型
"""
from sqlmodel import SQLModel

from .base import utc_now
from .emoji import EmojiTask
from .order import Order
from .points import PointTransaction, UserPoints
from .revenuecat import RevenueCatEvent
from .subscription import Subscription
from .user import User

__all__ = [
    "SQLModel",
    "utc_now",
    "User",
    "UserPoints",
    "PointTransaction",
    "Subscription",
    "Order",
    "EmojiTask",
    "RevenueCatEvent",
]
