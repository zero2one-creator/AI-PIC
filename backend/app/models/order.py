"""
订单模型模块

定义订单相关的数据库模型。
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Numeric, String
from sqlmodel import Field, SQLModel

from app.core.snowflake import generate_id
from app.enums import OrderStatus, ProductType

from .base import utc_now


class Order(SQLModel, table=True):
    """
    订单模型

    存储用户购买记录，包括积分包和订阅的订单信息。
    订单号唯一，用于防止重复支付。

    字段说明：
    - id: 主键
    - user_id: 用户 ID（外键）
    - order_no: 订单号（唯一，用于防重复）
    - product_type: 产品类型（积分包/订阅）
    - product_id: 产品 ID
    - quantity: 购买数量
    - amount: 订单金额（使用 Decimal 保证精度）
    - currency: 货币类型（默认 USD）
    - status: 订单状态（待支付/已支付/失败/退款）
    - payment_channel: 支付渠道（如 "apple", "google"）
    - transaction_id: 第三方支付平台的交易 ID
    - created_at: 创建时间
    - paid_at: 支付时间
    - updated_at: 更新时间
    """
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
