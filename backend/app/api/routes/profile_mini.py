from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps_mini import get_activated_user, get_db
from app.crud.user_mini import update_user
from app.models.user import User
from app.schemas.profile_mini import ProfileResponse, ProfileUpdateRequest

router = APIRouter(prefix="/profile", tags=["Profile"])


def build_profile_response(user: User) -> ProfileResponse:
    return ProfileResponse(
        id=user.id,
        openid=user.openid,
        nickname=user.nickname,
        goal=user.goal,
        height=user.height,
        weight=user.weight,
        avatar_url=user.avatar_url,
        is_activated=user.is_activated,
    )


def get_update_data(payload: ProfileUpdateRequest) -> dict:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=True)
    return payload.dict(exclude_unset=True)


@router.get("/me", response_model=ProfileResponse)
def get_my_profile(current_user: User = Depends(get_activated_user)):
    return build_profile_response(current_user)


@router.put("/me", response_model=ProfileResponse)
def update_my_profile(
    payload: ProfileUpdateRequest,
    current_user: User = Depends(get_activated_user),
    db: Session = Depends(get_db),
):
    user = update_user(db, current_user, get_update_data(payload))
    return build_profile_response(user)
