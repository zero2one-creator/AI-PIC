"""
积分模型模块

定义积分相关的数据库模型，包括用户积分账户和交易记录。
"""
from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, String
from sqlmodel import Field, SQLModel

from app.core.snowflake import generate_id
from app.enums import PointTransactionType

from .base import utc_now


class UserPoints(SQLModel, table=True):
    """
    用户积分账户模型

    存储每个用户的积分余额。每个用户只有一条积分记录（通过 unique=True 保证）。
    使用外键关联到 User 表，当用户被删除时，积分记录也会自动删除（CASCADE）。

    字段说明：
    - id: 主键
    - user_id: 用户 ID（外键，关联到 users 表）
    - balance: 当前积分余额
    - updated_at: 最后更新时间
    """
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
    """
    积分交易记录模型

    记录所有积分变动历史，用于审计和查询。每次积分变动都会创建一条记录。
    使用部分唯一索引防止同一用户在同一周重复领取周奖励。

    字段说明：
    - id: 主键
    - user_id: 用户 ID（外键）
    - type: 交易类型（消费/购买/奖励）
    - amount: 变动金额（负数表示扣除，正数表示增加）
    - balance_after: 交易后的余额（用于快速查询和验证）
    - task_type: 关联的任务类型（如 "emoji"）
    - order_no: 关联的订单号（购买积分时使用）
    - reward_week: 奖励周标识（格式如 "2024-W01"，用于周奖励去重）
    - created_at: 交易时间
    """
    __tablename__ = "point_transactions"
    __table_args__ = (
        Index(
            "idx_user_reward_week",
            "user_id",
            "reward_week",
            unique=True,
            postgresql_where=Column("reward_week").isnot(None),
        ),
    )

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

    amount: int = Field(nullable=False)
    balance_after: int = Field(nullable=False)

    task_type: str | None = Field(default=None, max_length=32)
    order_no: str | None = Field(default=None, max_length=64)
    reward_week: str | None = Field(default=None, max_length=8)

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
