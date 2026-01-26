"""
认证路由模块

处理用户登录相关的 API 端点。
使用设备 ID 进行登录（设备登录模式，无需密码）。
"""
from __future__ import annotations

from datetime import timedelta  # 时间间隔

from fastapi import APIRouter  # FastAPI 路由器

from app import crud  # 数据库操作
from app.api.deps import SessionDep  # 数据库会话依赖
from app.api.schemas import ApiEnvelope, AuthLoginData, AuthLoginRequest, UserProfile
from app.core import security  # 安全模块（JWT）
from app.core.config import settings

# 创建认证路由，所有路径都会添加 /auth 前缀
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=ApiEnvelope)
def login(session: SessionDep, body: AuthLoginRequest) -> ApiEnvelope:
    """
    用户登录接口

    使用设备 ID 登录，如果用户不存在则自动创建。
    登录成功后返回 JWT token 和用户信息。

    请求路径: POST /api/v1/auth/login

    Args:
        session: 数据库会话（自动注入）
        body: 登录请求数据（包含 device_id）

    Returns:
        ApiEnvelope: 包含 token 和用户信息的响应

    响应示例：
        {
            "code": 0,
            "message": "success",
            "data": {
                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                "expires_in": 604800,
                "user": {
                    "id": 123456789,
                    "device_id": "device-123",
                    "nickname": null,
                    "is_vip": false,
                    "points_balance": 100
                }
            }
        }
    """
    # 获取或创建用户（如果不存在则自动创建）
    user = crud.get_or_create_user_by_device_id(session=session, device_id=body.device_id)
    # 获取用户积分账户
    points_row = crud.get_user_points(session=session, user_id=user.id)

    # 生成 JWT token
    access_token_expires = timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
    token = security.create_access_token(user.id, expires_delta=access_token_expires)
    expires_in = int(access_token_expires.total_seconds())  # 转换为秒数

    # 构建用户资料
    profile = UserProfile(
        id=user.id,
        device_id=user.device_id,
        nickname=user.nickname,
        is_vip=user.is_vip,
        vip_type=user.vip_type,
        vip_expire_time=user.vip_expire_time,
        points_balance=points_row.balance,
    )
    # 构建登录响应数据
    data = AuthLoginData(access_token=token, expires_in=expires_in, user=profile)
    return ApiEnvelope(data=data)
