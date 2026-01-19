from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter

from app import crud
from app.api.deps import SessionDep
from app.api.schemas import ApiEnvelope, AuthLoginData, AuthLoginRequest, UserProfile
from app.core import security
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=ApiEnvelope)
def login(session: SessionDep, body: AuthLoginRequest) -> ApiEnvelope:
    user = crud.get_or_create_user_by_device_id(session=session, device_id=body.device_id)
    points_row = crud.get_user_points(session=session, user_id=user.id)

    access_token_expires = timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
    token = security.create_access_token(user.id, expires_delta=access_token_expires)
    expires_in = int(access_token_expires.total_seconds())

    profile = UserProfile(
        id=user.id,
        device_id=user.device_id,
        nickname=user.nickname,
        is_vip=user.is_vip,
        vip_type=user.vip_type,
        vip_expire_time=user.vip_expire_time,
        points_balance=points_row.balance,
    )
    data = AuthLoginData(access_token=token, expires_in=expires_in, user=profile)
    return ApiEnvelope(data=data)
