"""
表情生成任务模型模块

定义表情生成相关的数据库模型。
"""
from datetime import datetime

from sqlalchemy import JSON, BigInteger, Column, DateTime, ForeignKey, String, Text
from sqlmodel import Field, SQLModel

from app.core.snowflake import generate_id
from app.enums import EmojiTaskStatus

from .base import utc_now


class EmojiTask(SQLModel, table=True):
    """
    表情生成任务模型

    存储用户提交的表情生成任务，任务由后台 worker 异步处理。
    任务状态从 pending → processing → completed/failed。

    字段说明：
    - id: 主键
    - user_id: 用户 ID（外键）
    - driven_id: 驱动图片 ID（用于表情生成）
    - style_name: 表情风格名称（可选）
    - source_image_url: 源图片 URL（用户上传的图片）
    - detect_result: 图片检测结果（JSON，包含人脸检测等信息）
    - aliyun_task_id: 阿里云任务 ID（调用 AI 服务返回的任务标识）
    - result_url: 生成结果图片 URL（任务完成后）
    - status: 任务状态（待处理/处理中/已完成/失败）
    - points_cost: 任务消耗的积分
    - error_message: 错误信息（任务失败时）
    - created_at: 创建时间
    - completed_at: 完成时间
    """
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
