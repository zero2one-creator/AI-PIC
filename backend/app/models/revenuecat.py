"""
RevenueCat 事件模型模块

定义 RevenueCat webhook 事件相关的数据库模型。
"""
from datetime import datetime

from sqlalchemy import JSON, BigInteger, Column, DateTime, String
from sqlmodel import Field, SQLModel

from app.core.snowflake import generate_id

from .base import utc_now


class RevenueCatEvent(SQLModel, table=True):
    """
    RevenueCat Webhook 事件记录模型

    存储所有从 RevenueCat 接收到的 webhook 事件，用于去重和审计。
    通过 event_id 唯一性防止重复处理同一事件。

    字段说明：
    - id: 主键
    - event_id: RevenueCat 事件 ID（唯一，用于去重）
    - event_type: 事件类型（如 "INITIAL_PURCHASE", "RENEWAL" 等）
    - payload: 事件完整数据（JSON 格式）
    - created_at: 接收时间
    """
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
