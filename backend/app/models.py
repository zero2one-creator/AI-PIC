from datetime import datetime
from decimal import Decimal

from pydantic import EmailStr
from sqlmodel import Field, Relationship, SQLModel


# ============================================================================
# User Models
# ============================================================================

# Shared properties
class UserBase(SQLModel):
    email: EmailStr | None = Field(default=None, unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


# Device login
class DeviceLogin(SQLModel):
    device_id: str = Field(min_length=1, max_length=128)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=128)
    nickname: str | None = Field(default=None, max_length=64)
    is_vip: bool | None = None
    vip_type: str | None = Field(default=None, max_length=20)
    vip_expire_time: datetime | None = None


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)
    nickname: str | None = Field(default=None, max_length=64)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# Database model, database table inferred from class name
class User(SQLModel, table=True):
    id: int = Field(primary_key=True)  # Snowflake ID
    device_id: str | None = Field(default=None, max_length=128, index=True, unique=True)
    email: EmailStr | None = Field(default=None, max_length=255, index=True, unique=True)
    hashed_password: str | None = Field(default=None)
    nickname: str | None = Field(default=None, max_length=64)
    is_vip: bool = Field(default=False)
    vip_type: str | None = Field(default=None, max_length=20)  # weekly/lifetime
    vip_expire_time: datetime | None = Field(default=None)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    full_name: str | None = Field(default=None, max_length=255)
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    updated_at: datetime = Field(default_factory=lambda: datetime.utcnow())

    # Relationships
    items: list["Item"] = Relationship(back_populates="owner", cascade_delete=True)
    subscriptions: list["Subscription"] = Relationship(back_populates="user", cascade_delete=True)
    orders: list["Order"] = Relationship(back_populates="user", cascade_delete=True)
    emoji_tasks: list["EmojiTask"] = Relationship(back_populates="user", cascade_delete=True)


# Properties to return via API, id is always required
class UserPublic(SQLModel):
    id: int
    email: EmailStr | None
    device_id: str | None
    nickname: str | None
    is_vip: bool
    vip_type: str | None
    vip_expire_time: datetime | None
    is_active: bool
    is_superuser: bool
    full_name: str | None
    created_at: datetime


# User with points balance
class UserWithPoints(UserPublic):
    points_balance: int = 0


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# ============================================================================
# Item Models (保留原有的 Item 模型)
# ============================================================================

# Shared properties
class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on item creation
class ItemCreate(ItemBase):
    pass


# Properties to receive on item update
class ItemUpdate(ItemBase):
    title: str | None = Field(default=None, min_length=1, max_length=255)  # type: ignore


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    id: int = Field(primary_key=True)  # Snowflake ID
    owner_id: int = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="items")


# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    id: int
    owner_id: int


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


# ============================================================================
# Subscription Models
# ============================================================================

class SubscriptionBase(SQLModel):
    rc_subscriber_id: str = Field(max_length=128)
    product_id: str = Field(max_length=64)
    plan_type: str = Field(max_length=20)  # weekly/lifetime
    status: str = Field(max_length=20)  # active/cancelled/expired
    will_renew: bool = Field(default=True)
    current_period_start: datetime
    current_period_end: datetime


class SubscriptionCreate(SubscriptionBase):
    user_id: int


class SubscriptionUpdate(SQLModel):
    status: str | None = Field(default=None, max_length=20)
    will_renew: bool | None = None
    current_period_end: datetime | None = None
    cancelled_at: datetime | None = None


class Subscription(SubscriptionBase, table=True):
    id: int = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id", nullable=False, ondelete="CASCADE")
    cancelled_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    updated_at: datetime = Field(default_factory=lambda: datetime.utcnow())

    # Relationships
    user: User | None = Relationship(back_populates="subscriptions")


class SubscriptionPublic(SubscriptionBase):
    id: int
    user_id: int
    cancelled_at: datetime | None
    created_at: datetime


class SubscriptionsPublic(SQLModel):
    data: list[SubscriptionPublic]
    count: int


# ============================================================================
# Order Models
# ============================================================================

class OrderBase(SQLModel):
    order_no: str = Field(max_length=64, unique=True)
    product_type: str = Field(max_length=20)  # points_pack/subscription
    product_id: str = Field(max_length=64)
    quantity: int
    amount: Decimal = Field(max_digits=10, decimal_places=2)
    currency: str = Field(max_length=8)
    status: str = Field(max_length=20)  # pending/paid/failed/refunded
    payment_channel: str = Field(max_length=32)


class OrderCreate(OrderBase):
    user_id: int


class OrderUpdate(SQLModel):
    status: str | None = Field(default=None, max_length=20)
    transaction_id: str | None = Field(default=None, max_length=128)
    paid_at: datetime | None = None


class Order(OrderBase, table=True):
    id: int = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id", nullable=False, ondelete="CASCADE")
    transaction_id: str | None = Field(default=None, max_length=128)
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    paid_at: datetime | None = Field(default=None)
    updated_at: datetime = Field(default_factory=lambda: datetime.utcnow())

    # Relationships
    user: User | None = Relationship(back_populates="orders")


class OrderPublic(OrderBase):
    id: int
    user_id: int
    transaction_id: str | None
    created_at: datetime
    paid_at: datetime | None


class OrdersPublic(SQLModel):
    data: list[OrderPublic]
    count: int


# ============================================================================
# Points Models
# ============================================================================

class UserPointsBase(SQLModel):
    balance: int = Field(default=0)


class UserPoints(UserPointsBase, table=True):
    id: int = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True, nullable=False, ondelete="CASCADE")
    updated_at: datetime = Field(default_factory=lambda: datetime.utcnow())


class UserPointsPublic(UserPointsBase):
    id: int
    user_id: int
    updated_at: datetime


class PointTransactionBase(SQLModel):
    type: str = Field(max_length=20)  # consume/purchase/reward
    amount: int
    balance_after: int


class PointTransactionCreate(PointTransactionBase):
    user_id: int
    task_type: str | None = Field(default=None, max_length=32)
    order_id: str | None = Field(default=None, max_length=64)
    reward_week: str | None = Field(default=None, max_length=8)


class PointTransaction(PointTransactionBase, table=True):
    id: int = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True, nullable=False, ondelete="CASCADE")
    task_type: str | None = Field(default=None, max_length=32)
    order_id: str | None = Field(default=None, max_length=64)
    reward_week: str | None = Field(default=None, max_length=8)  # 2024-W03
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())


class PointTransactionPublic(PointTransactionBase):
    id: int
    user_id: int
    task_type: str | None
    order_id: str | None
    reward_week: str | None
    created_at: datetime


class PointTransactionsPublic(SQLModel):
    data: list[PointTransactionPublic]
    count: int


# ============================================================================
# Emoji Task Models
# ============================================================================

class EmojiTaskBase(SQLModel):
    task_type: str = Field(max_length=20)  # emoji/avatar/pose
    source_image_url: str = Field(max_length=512)
    driven_id: str = Field(max_length=64)
    status: str = Field(max_length=20)  # pending/processing/completed/failed
    points_cost: int


class EmojiTaskCreate(EmojiTaskBase):
    user_id: int
    face_bbox: str | None = None  # JSON string
    ext_bbox: str | None = None  # JSON string


class EmojiTaskUpdate(SQLModel):
    status: str | None = Field(default=None, max_length=20)
    ali_task_id: str | None = Field(default=None, max_length=128)
    result_url: str | None = Field(default=None, max_length=512)
    error_message: str | None = None
    completed_at: datetime | None = None


class EmojiTask(EmojiTaskBase, table=True):
    id: int = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True, nullable=False, ondelete="CASCADE")
    face_bbox: str | None = Field(default=None)  # JSON string
    ext_bbox: str | None = Field(default=None)  # JSON string
    ali_task_id: str | None = Field(default=None, max_length=128)
    result_url: str | None = Field(default=None, max_length=512)
    error_message: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    completed_at: datetime | None = Field(default=None)

    # Relationships
    user: User | None = Relationship(back_populates="emoji_tasks")


class EmojiTaskPublic(EmojiTaskBase):
    id: int
    user_id: int
    face_bbox: str | None
    ext_bbox: str | None
    ali_task_id: str | None
    result_url: str | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


class EmojiTasksPublic(SQLModel):
    data: list[EmojiTaskPublic]
    count: int


# ============================================================================
# Generic Models
# ============================================================================

# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"
    user: UserWithPoints


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)
