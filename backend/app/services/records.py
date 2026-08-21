import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.api.errors import APIError
from app.models.activity_record import ActivityRecord
from app.models.food_record import FoodRecord
from app.models.profile import Profile
from app.models.user import User
from app.models.weight_record import WeightRecord
from app.repositories.records import get_owned_for_update, list_owned
from app.schemas.common import Page, PageMeta
from app.schemas.records import (
    ActivityRecordCreate,
    ActivityRecordResponse,
    ActivityRecordUpdate,
    FoodRecordCreate,
    FoodRecordResponse,
    FoodRecordUpdate,
    WeightRecordCreate,
    WeightRecordResponse,
    WeightRecordUpdate,
)
from app.services.common import add_audit, require_resource_version, user_local_date


def _values(payload) -> dict[str, Any]:
    values = payload.model_dump(exclude_unset=True, mode="python")
    return {key: value.value if hasattr(value, "value") else value for key, value in values.items()}


def _not_found(resource: str) -> APIError:
    return APIError(
        status_code=404, code="record_not_found", message=f"{resource} record was not found"
    )


def _record_date(values: dict[str, Any], timestamp_field: str, profile: Profile) -> None:
    if timestamp_field in values:
        values["record_date"] = user_local_date(values[timestamp_field], profile.timezone)


def create_food(db: Session, user: User, payload: FoodRecordCreate, request_id: str) -> FoodRecord:
    values = _values(payload)
    _record_date(values, "recorded_at", user.profile)
    record = FoodRecord(user_id=user.id, **values)
    db.add(record)
    db.flush()
    add_audit(
        db,
        user_id=user.id,
        action="food.created",
        resource_type="food",
        resource_id=record.id,
        request_id=request_id,
    )
    return record


def update_food(
    db: Session,
    user: User,
    record_id: uuid.UUID,
    payload: FoodRecordUpdate,
    request_id: str,
    expected_version: int | None,
) -> FoodRecord:
    record = get_owned_for_update(db, FoodRecord, user.id, record_id)
    if record is None:
        raise _not_found("Food")
    require_resource_version(
        resource_type="food",
        resource_id=record.id,
        expected_version=expected_version,
        actual_version=record.version,
        server=FoodRecordResponse.model_validate(record).model_dump(mode="json"),
    )
    values = _values(payload)
    _record_date(values, "recorded_at", user.profile)
    for field, value in values.items():
        setattr(record, field, value)
    record.version += 1
    add_audit(
        db,
        user_id=user.id,
        action="food.updated",
        resource_type="food",
        resource_id=record.id,
        request_id=request_id,
    )
    db.commit()
    db.refresh(record)
    return record


def delete_food(
    db: Session,
    user: User,
    record_id: uuid.UUID,
    request_id: str,
    expected_version: int | None,
) -> None:
    record = get_owned_for_update(db, FoodRecord, user.id, record_id)
    if record is None:
        raise _not_found("Food")
    require_resource_version(
        resource_type="food",
        resource_id=record.id,
        expected_version=expected_version,
        actual_version=record.version,
        server=FoodRecordResponse.model_validate(record).model_dump(mode="json"),
    )
    db.delete(record)
    add_audit(
        db,
        user_id=user.id,
        action="food.deleted",
        resource_type="food",
        resource_id=record_id,
        request_id=request_id,
    )
    db.commit()


def list_food(db: Session, user: User, limit: int, offset: int) -> Page[FoodRecordResponse]:
    items, total = list_owned(
        db, FoodRecord, user.id, limit=limit, offset=offset, order_column=FoodRecord.recorded_at
    )
    return Page(
        items=[FoodRecordResponse.model_validate(item) for item in items],
        meta=PageMeta(limit=limit, offset=offset, total=total),
    )


def create_activity(
    db: Session, user: User, payload: ActivityRecordCreate, request_id: str
) -> ActivityRecord:
    values = _values(payload)
    _record_date(values, "recorded_at", user.profile)
    record = ActivityRecord(user_id=user.id, **values)
    db.add(record)
    db.flush()
    add_audit(
        db,
        user_id=user.id,
        action="activity.created",
        resource_type="activity",
        resource_id=record.id,
        request_id=request_id,
    )
    return record


def update_activity(
    db: Session,
    user: User,
    record_id: uuid.UUID,
    payload: ActivityRecordUpdate,
    request_id: str,
    expected_version: int | None,
) -> ActivityRecord:
    record = get_owned_for_update(db, ActivityRecord, user.id, record_id)
    if record is None:
        raise _not_found("Activity")
    require_resource_version(
        resource_type="activity",
        resource_id=record.id,
        expected_version=expected_version,
        actual_version=record.version,
        server=ActivityRecordResponse.model_validate(record).model_dump(mode="json"),
    )
    values = _values(payload)
    _record_date(values, "recorded_at", user.profile)
    for field, value in values.items():
        setattr(record, field, value)
    record.version += 1
    add_audit(
        db,
        user_id=user.id,
        action="activity.updated",
        resource_type="activity",
        resource_id=record.id,
        request_id=request_id,
    )
    db.commit()
    db.refresh(record)
    return record


def delete_activity(
    db: Session,
    user: User,
    record_id: uuid.UUID,
    request_id: str,
    expected_version: int | None,
) -> None:
    record = get_owned_for_update(db, ActivityRecord, user.id, record_id)
    if record is None:
        raise _not_found("Activity")
    require_resource_version(
        resource_type="activity",
        resource_id=record.id,
        expected_version=expected_version,
        actual_version=record.version,
        server=ActivityRecordResponse.model_validate(record).model_dump(mode="json"),
    )
    db.delete(record)
    add_audit(
        db,
        user_id=user.id,
        action="activity.deleted",
        resource_type="activity",
        resource_id=record_id,
        request_id=request_id,
    )
    db.commit()


def list_activity(db: Session, user: User, limit: int, offset: int) -> Page[ActivityRecordResponse]:
    items, total = list_owned(
        db,
        ActivityRecord,
        user.id,
        limit=limit,
        offset=offset,
        order_column=ActivityRecord.recorded_at,
    )
    return Page(
        items=[ActivityRecordResponse.model_validate(item) for item in items],
        meta=PageMeta(limit=limit, offset=offset, total=total),
    )


def create_weight(
    db: Session, user: User, payload: WeightRecordCreate, request_id: str
) -> WeightRecord:
    values = _values(payload)
    _record_date(values, "measured_at", user.profile)
    record = WeightRecord(user_id=user.id, **values)
    db.add(record)
    db.flush()
    add_audit(
        db,
        user_id=user.id,
        action="weight.created",
        resource_type="weight",
        resource_id=record.id,
        request_id=request_id,
    )
    return record


def update_weight(
    db: Session,
    user: User,
    record_id: uuid.UUID,
    payload: WeightRecordUpdate,
    request_id: str,
    expected_version: int | None,
) -> WeightRecord:
    record = get_owned_for_update(db, WeightRecord, user.id, record_id)
    if record is None:
        raise _not_found("Weight")
    require_resource_version(
        resource_type="weight",
        resource_id=record.id,
        expected_version=expected_version,
        actual_version=record.version,
        server=WeightRecordResponse.model_validate(record).model_dump(mode="json"),
    )
    values = _values(payload)
    _record_date(values, "measured_at", user.profile)
    for field, value in values.items():
        setattr(record, field, value)
    record.version += 1
    add_audit(
        db,
        user_id=user.id,
        action="weight.updated",
        resource_type="weight",
        resource_id=record.id,
        request_id=request_id,
    )
    db.commit()
    db.refresh(record)
    return record


def delete_weight(
    db: Session,
    user: User,
    record_id: uuid.UUID,
    request_id: str,
    expected_version: int | None,
) -> None:
    record = get_owned_for_update(db, WeightRecord, user.id, record_id)
    if record is None:
        raise _not_found("Weight")
    require_resource_version(
        resource_type="weight",
        resource_id=record.id,
        expected_version=expected_version,
        actual_version=record.version,
        server=WeightRecordResponse.model_validate(record).model_dump(mode="json"),
    )
    db.delete(record)
    add_audit(
        db,
        user_id=user.id,
        action="weight.deleted",
        resource_type="weight",
        resource_id=record_id,
        request_id=request_id,
    )
    db.commit()


def list_weight(db: Session, user: User, limit: int, offset: int) -> Page[WeightRecordResponse]:
    items, total = list_owned(
        db, WeightRecord, user.id, limit=limit, offset=offset, order_column=WeightRecord.measured_at
    )
    return Page(
        items=[WeightRecordResponse.model_validate(item) for item in items],
        meta=PageMeta(limit=limit, offset=offset, total=total),
    )
