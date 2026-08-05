import uuid

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.goal import Goal
from app.models.profile import Profile
from app.models.user import User
from app.models.weight_record import WeightRecord
from app.schemas.profile import (
    GoalResponse,
    GoalUpsertRequest,
    ProfileResponse,
    ProfileUpdateRequest,
)
from app.services.common import add_audit


def profile_response(db: Session, profile: Profile) -> ProfileResponse:
    latest_weight = db.scalar(
        select(WeightRecord.weight_kg)
        .where(WeightRecord.user_id == profile.user_id)
        .order_by(WeightRecord.measured_at.desc(), WeightRecord.id.desc())
        .limit(1)
    )
    return ProfileResponse(
        user_id=profile.user_id,
        display_name=profile.display_name,
        timezone=profile.timezone,
        locale=profile.locale,
        sex=profile.sex,
        birth_date=profile.birth_date,
        height_cm=float(profile.height_cm) if profile.height_cm is not None else None,
        preferred_unit=profile.preferred_unit,
        latest_weight_kg=float(latest_weight) if latest_weight is not None else None,
        updated_at=profile.updated_at,
    )


def get_profile(db: Session, user: User) -> ProfileResponse:
    return profile_response(db, user.profile)


def update_profile(
    db: Session,
    user: User,
    payload: ProfileUpdateRequest,
    request_id: str,
) -> ProfileResponse:
    for field, value in payload.model_dump(exclude_unset=True, mode="python").items():
        setattr(user.profile, field, value.value if hasattr(value, "value") else value)
    add_audit(
        db,
        user_id=user.id,
        action="profile.updated",
        resource_type="profile",
        resource_id=user.id,
        request_id=request_id,
        event_data={"fields": sorted(payload.model_fields_set)},
    )
    db.commit()
    db.refresh(user.profile)
    return profile_response(db, user.profile)


def get_active_goal(db: Session, user_id: uuid.UUID) -> Goal | None:
    return db.scalar(
        select(Goal)
        .where(Goal.user_id == user_id, Goal.is_active.is_(True))
        .order_by(Goal.updated_at.desc())
        .limit(1)
    )


def upsert_goal(
    db: Session,
    user: User,
    payload: GoalUpsertRequest,
    request_id: str,
) -> GoalResponse:
    current = get_active_goal(db, user.id)
    values = payload.model_dump(mode="python")
    values["kind"] = payload.kind.value
    if current is None:
        current = Goal(user_id=user.id, **values)
        db.add(current)
    else:
        for field, value in values.items():
            setattr(current, field, value)
    db.flush()
    add_audit(
        db,
        user_id=user.id,
        action="goal.upserted",
        resource_type="goal",
        resource_id=current.id,
        request_id=request_id,
    )
    db.commit()
    db.refresh(current)
    return GoalResponse.model_validate(current)


def clear_active_goals(db: Session, user_id: uuid.UUID) -> None:
    db.execute(update(Goal).where(Goal.user_id == user_id).values(is_active=False))
