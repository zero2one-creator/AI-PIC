from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    JSON,
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
)
from sqlmodel import Field, SQLModel

from app.core.snowflake import generate_id


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class VipType(str, Enum):
    weekly = "weekly"
    lifetime = "lifetime"


class SubscriptionStatus(str, Enum):
    active = "active"
    cancelled = "cancelled"
    expired = "expired"


class OrderStatus(str, Enum):
    pending = "pending"
    paid = "paid"
    failed = "failed"
    refunded = "refunded"


class ProductType(str, Enum):
    points_pack = "points_pack"
    subscription = "subscription"


class PointTransactionType(str, Enum):
    consume = "consume"
    purchase = "purchase"
    reward = "reward"


class EmojiTaskStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class User(SQLModel, table=True):
    __tablename__ = "users"
    id: int = Field(
        default_factory=generate_id,
        sa_column=Column(BigInteger, primary_key=True, autoincrement=False),
    )
    device_id: str = Field(
        max_length=128,
        sa_column=Column(String(128), unique=True, index=True, nullable=False),
    )
    nickname: str | None = Field(default=None, max_length=64)

    is_vip: bool = Field(default=False)
    vip_type: VipType | None = Field(
        default=None, sa_column=Column(String(16), nullable=True)
    )
    vip_expire_time: datetime | None = Field(
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


class UserPoints(SQLModel, table=True):
    __tablename__ = "user_points"
    id: int = Field(
        default_factory=generate_id,
        sa_column=Column(BigInteger, primary_key=True, autoincrement=False),
    )
    user_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey("users.id", ondelete="CASCADE"),
            index=True,
            nullable=False,
            unique=True,
        )
    )
    balance: int = Field(default=0)
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class PointTransaction(SQLModel, table=True):
    __tablename__ = "point_transactions"
    id: int = Field(
        default_factory=generate_id,
        sa_column=Column(BigInteger, primary_key=True, autoincrement=False),
    )
    user_id: int = Field(
        sa_column=Column(
            BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
        )
    )
    type: PointTransactionType = Field(sa_column=Column(String(16), nullable=False))

    # Negative for consume, positive for purchase/reward
    amount: int = Field(nullable=False)
    balance_after: int = Field(nullable=False)

    task_type: str | None = Field(default=None, max_length=32)
    order_no: str | None = Field(default=None, max_length=64)
    reward_week: str | None = Field(default=None, max_length=8)

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class Subscription(SQLModel, table=True):
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


class Order(SQLModel, table=True):
    __tablename__ = "orders"
    id: int = Field(
        default_factory=generate_id,
        sa_column=Column(BigInteger, primary_key=True, autoincrement=False),
    )
    user_id: int = Field(
        sa_column=Column(
            BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
        )
    )

    order_no: str = Field(
        sa_column=Column(String(64), unique=True, index=True, nullable=False)
    )
    product_type: ProductType = Field(sa_column=Column(String(16), nullable=False))
    product_id: str = Field(max_length=64)
    quantity: int = Field(default=1)

    amount: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=Column(Numeric(10, 2), nullable=False),
    )
    currency: str = Field(default="USD", max_length=8)

    status: OrderStatus = Field(sa_column=Column(String(16), nullable=False))
    payment_channel: str | None = Field(default=None, max_length=32)
    transaction_id: str | None = Field(default=None, max_length=128)

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    paid_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class EmojiTask(SQLModel, table=True):
    __tablename__ = "emoji_tasks"
    id: int = Field(
        default_factory=generate_id,
        sa_column=Column(BigInteger, primary_key=True, autoincrement=False),
    )
    user_id: int = Field(
        sa_column=Column(
            BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
        )
    )

    driven_id: str = Field(max_length=64)
    style_name: str | None = Field(default=None, max_length=64)
    source_image_url: str = Field(max_length=512)
    detect_result: dict | None = Field(default=None, sa_column=Column(JSON))

    aliyun_task_id: str | None = Field(default=None, max_length=128)
    result_url: str | None = Field(default=None, max_length=512)

    status: EmojiTaskStatus = Field(sa_column=Column(String(16), nullable=False))
    points_cost: int = Field(default=0)

    error_message: str | None = Field(default=None, sa_column=Column(Text))

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    completed_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )


class RevenueCatEvent(SQLModel, table=True):
    __tablename__ = "revenuecat_events"

    id: int = Field(
        default_factory=generate_id,
        sa_column=Column(BigInteger, primary_key=True, autoincrement=False),
    )
    event_id: str = Field(sa_column=Column(String(64), unique=True, index=True, nullable=False))
    event_type: str = Field(max_length=64)
    payload: dict | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class Message(SQLModel):
    message: str


class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(SQLModel):
    sub: str | None = None
