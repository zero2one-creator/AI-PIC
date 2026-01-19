from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.models import (
    EmojiTaskStatus,
    OrderStatus,
    PointTransactionType,
    ProductType,
    VipType,
)


class ApiEnvelope(BaseModel):
    code: int = 0
    message: str = "success"
    data: Any | None = None


class AuthLoginRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=128)


class UserProfile(BaseModel):
    id: int
    device_id: str
    nickname: str | None = None
    is_vip: bool
    vip_type: VipType | None = None
    vip_expire_time: datetime | None = None
    points_balance: int


class UserProfileUpdateRequest(BaseModel):
    nickname: str | None = Field(default=None, max_length=64)


class AuthLoginData(BaseModel):
    access_token: str
    expires_in: int
    user: UserProfile


class PointsBalanceData(BaseModel):
    balance: int


class PointTransactionPublic(BaseModel):
    id: int
    type: PointTransactionType
    amount: int
    balance_after: int
    task_type: str | None = None
    order_no: str | None = None
    reward_week: str | None = None
    created_at: datetime


class PointsTransactionsData(BaseModel):
    data: list[PointTransactionPublic]
    count: int


class ConfigData(BaseModel):
    banners: list[dict[str, Any]] = []
    styles: list[dict[str, Any]] = []
    points_rules: dict[str, Any] = {}
    weekly_reward: dict[str, Any] = {}
    vip_products: dict[str, Any] = {}
    points_packs: dict[str, Any] = {}


class OssUploadData(BaseModel):
    host: str
    dir: str
    key: str
    policy: str
    signature: str
    access_key_id: str
    expire_at: int
    image_url: str


class EmojiDetectRequest(BaseModel):
    image_url: str = Field(min_length=1, max_length=1024)


class EmojiDetectData(BaseModel):
    passed: bool
    face_bbox: list[int] | None = None
    ext_bbox: list[int] | None = None
    raw: dict[str, Any] | None = None


class EmojiCreateRequest(BaseModel):
    image_url: str = Field(min_length=1, max_length=1024)
    driven_id: str = Field(min_length=1, max_length=64)
    face_bbox: list[int] | None = None
    ext_bbox: list[int] | None = None


class EmojiTaskData(BaseModel):
    id: int
    status: EmojiTaskStatus
    points_cost: int
    result_url: str | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class EmojiHistoryData(BaseModel):
    data: list[EmojiTaskData]
    count: int


class SubscriptionStatusData(BaseModel):
    is_vip: bool
    vip_type: VipType | None = None
    vip_expire_time: datetime | None = None


class OrderCreateRequest(BaseModel):
    product_type: ProductType
    product_id: str = Field(min_length=1, max_length=64)
    quantity: int = Field(default=1, ge=1, le=100000)
    amount: Decimal = Decimal("0.00")
    currency: str = Field(default="USD", max_length=8)


class OrderData(BaseModel):
    order_no: str
    product_type: ProductType
    product_id: str
    quantity: int
    amount: Decimal
    currency: str
    status: OrderStatus
    created_at: datetime


class OrdersData(BaseModel):
    data: list[OrderData]
    count: int
