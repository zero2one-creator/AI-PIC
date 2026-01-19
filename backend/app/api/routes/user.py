from __future__ import annotations

from fastapi import APIRouter

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.api.schemas import ApiEnvelope, UserProfile, UserProfileUpdateRequest
from app.models import utc_now

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/profile", response_model=ApiEnvelope)
def profile(session: SessionDep, current_user: CurrentUser) -> ApiEnvelope:
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
    nickname = body.nickname
    if nickname is not None:
        nickname = nickname.strip()
        if nickname == "":
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
