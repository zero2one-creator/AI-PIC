"""
用户模型模块

定义用户相关的数据库模型。
"""
from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, String
from sqlmodel import Field, SQLModel

from app.core.snowflake import generate_id
from app.enums import VipType

from .base import utc_now


class User(SQLModel, table=True):
    """
    用户模型

    存储用户基本信息，使用设备 ID 作为唯一标识（设备登录模式）。
    每个用户可以有 VIP 订阅状态。

    字段说明：
    - id: 主键，使用 Snowflake 算法生成的分布式唯一 ID
    - device_id: 设备唯一标识，用于登录认证（唯一且建立索引）
    - nickname: 用户昵称（可选）
    - is_vip: 是否为 VIP 用户
    - vip_type: VIP 类型（周订阅或终身）
    - vip_expire_time: VIP 过期时间（终身会员为 None）
    - created_at: 创建时间（自动设置）
    - updated_at: 更新时间（自动设置）
    """
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
