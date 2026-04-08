from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.crud.profile import get_or_create_profile, update_profile
from app.models.profile import Profile
from app.models.user import User
from app.schemas.profile import ProfileResponse, ProfileUpdateRequest

router = APIRouter(prefix="/profile", tags=["Profile"])


def build_profile_response(profile: Profile) -> ProfileResponse:
    return ProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        nickname=profile.nickname,
        account=profile.account,
        goal=profile.goal,
        reminder_enabled=profile.reminder_enabled,
        unit=profile.unit,
        gender=profile.gender,
        age=profile.age,
        height=profile.height,
        weight=profile.weight,
        target_weight=profile.target_weight,
        goal_text=profile.goal_text,
    )


def get_update_data(payload: ProfileUpdateRequest) -> dict:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=True)
    return payload.dict(exclude_unset=True)


@router.get("/me", response_model=ProfileResponse)
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = get_or_create_profile(db, current_user.id, current_user.username)
    return build_profile_response(profile)


@router.put("/me", response_model=ProfileResponse)
def update_my_profile(
    payload: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = get_or_create_profile(db, current_user.id, current_user.username)
    next_profile = update_profile(db, profile, get_update_data(payload))
    return build_profile_response(next_profile)