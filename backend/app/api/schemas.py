"""
API 请求/响应数据模型（Schema）

定义所有 API 接口的请求和响应数据结构。
使用 Pydantic 进行数据验证和序列化。

关键概念：
- BaseModel: Pydantic 的模型基类，用于数据验证
- Field: 字段验证器，定义字段的约束（长度、范围等）
- 这些模型不是数据库表，只用于 API 数据交换
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal  # 精确数值类型，用于金额
from typing import Any  # 任意类型

from pydantic import BaseModel, Field  # Pydantic 核心类

from app.enums import (
    EmojiTaskStatus,  # 表情任务状态枚举
    OrderStatus,  # 订单状态枚举
    PointTransactionType,  # 积分交易类型枚举
    ProductType,  # 产品类型枚举
    VipType,  # VIP 类型枚举
)

# ============================================================
# 通用响应模型
# ============================================================


class Message(BaseModel):
    """
    消息响应模型

    用于 API 返回简单的文本消息。
    """
    message: str


class Token(BaseModel):
    """
    认证令牌响应模型

    用于登录接口返回 JWT token 信息。
    符合 OAuth2 标准的响应格式。
    """
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """
    JWT Token 载荷模型

    用于解析 JWT token 中的用户信息。
    sub (subject) 通常存储用户 ID 或设备 ID。
    """
    sub: str | None = None


# ============================================================
# API 响应模型
# ============================================================


class ApiEnvelope(BaseModel):
    """
    API 统一响应格式

    所有 API 响应都使用这个格式，包含：
    - code: 状态码（0 表示成功，非 0 表示错误）
    - message: 消息（成功时为 "success"，错误时为错误描述）
    - data: 数据（成功时返回业务数据，错误时为 None）

    示例响应：
        {"code": 0, "message": "success", "data": {...}}
        {"code": 402001, "message": "积分不足", "data": None}
    """
    code: int = 0  # 默认成功
    message: str = "success"  # 默认成功消息
    data: Any | None = None  # 业务数据（可选）


class AuthLoginRequest(BaseModel):
    """
    登录请求模型

    设备登录模式，只需要设备 ID 即可登录。
    """
    device_id: str = Field(min_length=1, max_length=128)  # 设备 ID，必填


class UserProfile(BaseModel):
    """
    用户资料模型

    用于返回用户信息，包含基本信息和积分余额。
    """
    id: int  # 用户 ID
    device_id: str  # 设备 ID
    nickname: str | None = None  # 昵称（可选）
    is_vip: bool  # 是否为 VIP
    vip_type: VipType | None = None  # VIP 类型
    vip_expire_time: datetime | None = None  # VIP 过期时间
    points_balance: int  # 积分余额


class UserProfileUpdateRequest(BaseModel):
    """
    更新用户资料请求模型

    目前只支持更新昵称。
    """
    nickname: str | None = Field(default=None, max_length=64)  # 新昵称（可选）


class AuthLoginData(BaseModel):
    """
    登录响应数据模型

    登录成功后返回 token 和用户信息。
    """
    access_token: str  # JWT 访问令牌
    expires_in: int  # token 过期时间（秒）
    user: UserProfile  # 用户信息


class PointsBalanceData(BaseModel):
    """
    积分余额响应模型

    返回用户当前积分余额。
    """
    balance: int  # 积分余额


class PointTransactionPublic(BaseModel):
    """
    积分交易记录公开模型

    用于返回积分交易历史，不包含敏感信息。
    """
    id: int  # 交易 ID
    type: PointTransactionType  # 交易类型（消费/购买/奖励）
    amount: int  # 变动金额（负数表示扣除）
    balance_after: int  # 交易后余额
    task_type: str | None = None  # 关联任务类型
    order_no: str | None = None  # 关联订单号
    reward_week: str | None = None  # 奖励周标识
    created_at: datetime  # 交易时间


class PointsTransactionsData(BaseModel):
    """
    积分交易列表响应模型

    返回积分交易历史列表和总数。
    """
    data: list[PointTransactionPublic]  # 交易记录列表
    count: int  # 总记录数


class ConfigData(BaseModel):
    """
    应用配置数据模型

    返回前端需要的所有配置信息，包括：
    - 轮播图、表情风格、积分规则、VIP 产品等
    """
    banners: list[dict[str, Any]] = []  # 轮播图列表
    styles: list[dict[str, Any]] = []  # 表情风格列表
    points_rules: dict[str, Any] = {}  # 积分规则
    weekly_reward: dict[str, Any] = {}  # 周奖励配置
    vip_products: dict[str, Any] = {}  # VIP 产品配置
    points_packs: dict[str, Any] = {}  # 积分包配置


class EmojiDetectData(BaseModel):
    """
    表情检测响应模型

    返回上传的图片 URL 和检测结果。
    """
    image_url: str  # 上传后的图片 URL
    passed: bool  # 是否通过检测
    face_bbox: list[int] | None = None  # 人脸边界框 [x, y, width, height]
    ext_bbox: list[int] | None = None  # 扩展边界框
    raw: dict[str, Any] | None = None  # 原始检测数据（用于调试）


class EmojiCreateRequest(BaseModel):
    """
    创建表情任务请求模型

    提交表情生成任务，需要源图片和驱动图片。
    """
    image_url: str = Field(min_length=1, max_length=1024)  # 源图片 URL
    driven_id: str = Field(min_length=1, max_length=64)  # 驱动图片 ID
    face_bbox: list[int] | None = None  # 人脸边界框（可选，用于优化）
    ext_bbox: list[int] | None = None  # 扩展边界框（可选）


class EmojiTaskData(BaseModel):
    """
    表情任务数据模型

    返回任务的状态和结果信息。
    """
    id: int  # 任务 ID
    status: EmojiTaskStatus  # 任务状态
    points_cost: int  # 消耗的积分
    result_url: str | None = None  # 生成结果 URL（完成时）
    error_message: str | None = None  # 错误信息（失败时）
    created_at: datetime  # 创建时间
    completed_at: datetime | None = None  # 完成时间


class EmojiHistoryData(BaseModel):
    """
    表情历史列表响应模型

    返回用户的表情生成历史。
    """
    data: list[EmojiTaskData]  # 任务列表
    count: int  # 总记录数


class SubscriptionStatusData(BaseModel):
    """
    订阅状态响应模型

    返回用户的 VIP 订阅状态。
    """
    is_vip: bool  # 是否为 VIP
    vip_type: VipType | None = None  # VIP 类型
    vip_expire_time: datetime | None = None  # VIP 过期时间


class OrderCreateRequest(BaseModel):
    """
    创建订单请求模型

    用户购买积分包或订阅时提交的订单信息。
    """
    product_type: ProductType  # 产品类型（积分包/订阅）
    product_id: str = Field(min_length=1, max_length=64)  # 产品 ID
    quantity: int = Field(default=1, ge=1, le=100000)  # 购买数量（1-100000）
    amount: Decimal = Decimal("0.00")  # 订单金额
    currency: str = Field(default="USD", max_length=8)  # 货币类型


class OrderData(BaseModel):
    """
    订单数据模型

    返回订单的详细信息。
    """
    order_no: str  # 订单号
    product_type: ProductType  # 产品类型
    product_id: str  # 产品 ID
    quantity: int  # 数量
    amount: Decimal  # 金额
    currency: str  # 货币
    status: OrderStatus  # 订单状态
    created_at: datetime  # 创建时间


class OrdersData(BaseModel):
    """
    订单列表响应模型

    返回用户的订单历史。
    """
    data: list[OrderData]  # 订单列表
    count: int  # 总记录数
