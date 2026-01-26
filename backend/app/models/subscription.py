"""
订阅模型模块

定义订阅相关的数据库模型。
"""
from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String
from sqlmodel import Field, SQLModel

from app.core.snowflake import generate_id
from app.enums import SubscriptionStatus, VipType

from .base import utc_now


class Subscription(SQLModel, table=True):
    """
    订阅记录模型

    存储用户的 RevenueCat 订阅信息，用于管理 iOS/Android 应用的订阅状态。
    通过 RevenueCat webhook 更新订阅状态。

    字段说明：
    - id: 主键
    - user_id: 用户 ID（外键）
    - rc_subscriber_id: RevenueCat 订阅者 ID
    - product_id: 产品 ID（RevenueCat 中的产品标识）
    - plan_type: 订阅计划类型（周订阅/终身）
    - status: 订阅状态（激活/取消/过期）
    - will_renew: 是否会自动续费
    - current_period_start: 当前订阅周期开始时间
    - current_period_end: 当前订阅周期结束时间
    - cancelled_at: 取消时间
    - created_at: 创建时间
    - updated_at: 更新时间
    """
    __tablename__ = "subscriptions"
    id: int = Field(
        default_factory=generate_id,
        sa_column=Column(BigInteger, primary_key=True, autoincrement=False),
    )
    user_id: int = Field(
        sa_column=Column(
            BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
        )
    )

    rc_subscriber_id: str = Field(max_length=128)
    product_id: str = Field(max_length=64)
    plan_type: VipType = Field(sa_column=Column(String(16), nullable=False))

    status: SubscriptionStatus = Field(sa_column=Column(String(16), nullable=False))
    will_renew: bool = Field(default=True)

    current_period_start: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    current_period_end: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    cancelled_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
