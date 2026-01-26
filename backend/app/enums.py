"""
枚举类型定义模块

定义应用中使用的所有枚举类型。
枚举用于限制字段只能取特定的值，提供类型安全和代码可读性。

所有枚举都继承自 str 和 Enum，这样既可以用作字符串，又具有枚举的特性。
"""
from enum import Enum  # 枚举类型，用于定义固定的选项集合


class VipType(str, Enum):
    """
    VIP 类型枚举

    定义用户订阅的类型：
    - weekly: 周订阅
    - lifetime: 终身会员
    """
    weekly = "weekly"
    lifetime = "lifetime"


class SubscriptionStatus(str, Enum):
    """
    订阅状态枚举

    定义订阅的当前状态：
    - active: 激活中
    - cancelled: 已取消
    - expired: 已过期
    """
    active = "active"
    cancelled = "cancelled"
    expired = "expired"


class OrderStatus(str, Enum):
    """
    订单状态枚举

    定义订单的处理状态：
    - pending: 待支付
    - paid: 已支付
    - failed: 支付失败
    - refunded: 已退款
    """
    pending = "pending"
    paid = "paid"
    failed = "failed"
    refunded = "refunded"


class ProductType(str, Enum):
    """
    产品类型枚举

    定义可购买的产品类型：
    - points_pack: 积分包
    - subscription: 订阅服务
    """
    points_pack = "points_pack"
    subscription = "subscription"


class PointTransactionType(str, Enum):
    """
    积分交易类型枚举

    定义积分变动的类型：
    - consume: 消费（扣除积分，如生成表情）
    - purchase: 购买（增加积分，如购买积分包）
    - reward: 奖励（增加积分，如 VIP 周奖励）
    """
    consume = "consume"
    purchase = "purchase"
    reward = "reward"


class EmojiTaskStatus(str, Enum):
    """
    表情生成任务状态枚举

    定义任务的处理状态：
    - pending: 待处理（已创建，等待 worker 处理）
    - processing: 处理中（worker 正在调用 AI 服务）
    - completed: 已完成（成功生成表情）
    - failed: 失败（处理出错）
    """
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"
