"""
用户路由模块

处理用户相关的 API 端点，包括：
- 获取用户资料（包含积分余额）
- 更新用户资料（昵称等）
"""
from __future__ import annotations

from fastapi import APIRouter

from app import crud  # 数据库操作
from app.api.deps import CurrentUser, SessionDep  # 依赖注入
from app.api.schemas import ApiEnvelope, UserProfile, UserProfileUpdateRequest
from app.models import utc_now  # UTC 时间工具

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/profile", response_model=ApiEnvelope)
def profile(session: SessionDep, current_user: CurrentUser) -> ApiEnvelope:
    """
    获取用户资料

    返回当前登录用户的完整资料信息，包括基本信息和积分余额。

    请求路径: GET /api/v1/user/profile

    Args:
        session: 数据库会话
        current_user: 当前登录用户（自动注入）

    Returns:
        ApiEnvelope: 包含用户资料的响应
    """
    points_row = crud.get_user_points(session=session, user_id=current_user.id)
    data = UserProfile(
        id=current_user.id,
        device_id=current_user.device_id,
        nickname=current_user.nickname,
        is_vip=current_user.is_vip,
        vip_type=current_user.vip_type,
        vip_expire_time=current_user.vip_expire_time,
        points_balance=points_row.balance,
    )
    return ApiEnvelope(data=data)


@router.put("/profile", response_model=ApiEnvelope)
def update_profile(
    session: SessionDep,
    current_user: CurrentUser,
    body: UserProfileUpdateRequest,
) -> ApiEnvelope:
    """
    更新用户资料

    更新当前登录用户的资料信息（目前只支持更新昵称）。
    空字符串会被转换为 None。

    请求路径: PUT /api/v1/user/profile

    Args:
        session: 数据库会话
        current_user: 当前登录用户
        body: 更新请求数据

    Returns:
        ApiEnvelope: 包含更新后用户资料的响应
    """
    nickname = body.nickname
    if nickname is not None:
        nickname = nickname.strip()  # 去除首尾空格
        if nickname == "":
            # 空字符串转换为 None
            nickname = None

    current_user.nickname = nickname
    current_user.updated_at = utc_now()
    session.add(current_user)
    session.commit()
    session.refresh(current_user)

    points_row = crud.get_user_points(session=session, user_id=current_user.id)
    data = UserProfile(
        id=current_user.id,
        device_id=current_user.device_id,
        nickname=current_user.nickname,
        is_vip=current_user.is_vip,
        vip_type=current_user.vip_type,
        vip_expire_time=current_user.vip_expire_time,
        points_balance=points_row.balance,
    )
    return ApiEnvelope(data=data)
