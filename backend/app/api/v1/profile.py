from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.errors import APIError
from app.core.database import get_db
from app.models.user import User
from app.schemas.profile import (
    GoalResponse,
    GoalUpsertRequest,
    ProfileResponse,
    ProfileUpdateRequest,
)
from app.services import profile as profile_service

router = APIRouter(tags=["Profile"])


@router.get("/profile", response_model=ProfileResponse)
def get_profile(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ProfileResponse:
    return profile_service.get_profile(db, user)


@router.patch("/profile", response_model=ProfileResponse)
def update_profile(
    payload: ProfileUpdateRequest,
    request: Request,
    expected_version: int | None = Header(default=None, alias="If-Match-Version", ge=1),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    return profile_service.update_profile(
        db, user, payload, request.state.request_id, expected_version
    )


@router.get("/goals/current", response_model=GoalResponse)
def get_goal(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> GoalResponse:
    goal = profile_service.get_active_goal(db, user.id)
    if goal is None:
        raise APIError(status_code=404, code="goal_not_found", message="No active goal exists")
    return GoalResponse.model_validate(goal)


@router.put("/goals/current", response_model=GoalResponse)
def upsert_goal(
    payload: GoalUpsertRequest,
    request: Request,
    expected_version: int | None = Header(default=None, alias="If-Match-Version", ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GoalResponse:
    return profile_service.upsert_goal(
        db, user, payload, request.state.request_id, expected_version
    )
