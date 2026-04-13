from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps_mini import get_activated_user, get_db
from app.crud.activity_record import (
    create_activity_record,
    delete_activity_record,
    get_activity_record_by_id,
    list_activity_records,
    update_activity_record,
)
from app.models.activity_record import ActivityRecord
from app.models.user import User
from app.schemas.activity_record_mini import (
    ActivityRecordCreateRequest,
    ActivityRecordResponse,
    ActivityRecordUpdateRequest,
    MessageResponse,
)

router = APIRouter(prefix="/activity-records", tags=["Mini Activity Records"])


def build_activity_record_response(record: ActivityRecord) -> ActivityRecordResponse:
    return ActivityRecordResponse(
        id=record.id,
        user_id=record.user_id,
        record_date=record.record_date,
        time_text=record.time_text,
        name=record.name,
        location=record.location,
        kcal=record.kcal,
        source_type=record.source_type,
        ai_type=record.ai_type,
        extra={
            "source": {
                "source_type": record.source_type,
                "ai_type": record.ai_type,
            }
        },
    )


def get_payload_data(payload) -> dict:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=True)
    return payload.dict(exclude_unset=True)


@router.get("", response_model=list[ActivityRecordResponse])
def get_my_activity_records(
    record_date: Optional[date] = Query(default=None),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_activated_user),
    db: Session = Depends(get_db),
):
    records = list_activity_records(
        db=db,
        user_id=current_user.id,
        record_date=record_date,
        start_date=start_date,
        end_date=end_date,
    )
    return [build_activity_record_response(record) for record in records[:limit]]


@router.post("", response_model=ActivityRecordResponse)
def create_my_activity_record(
    payload: ActivityRecordCreateRequest,
    current_user: User = Depends(get_activated_user),
    db: Session = Depends(get_db),
):
    record = create_activity_record(db=db, user_id=current_user.id, data=get_payload_data(payload))
    return build_activity_record_response(record)


@router.put("/{record_id}", response_model=ActivityRecordResponse)
def update_my_activity_record(
    record_id: int,
    payload: ActivityRecordUpdateRequest,
    current_user: User = Depends(get_activated_user),
    db: Session = Depends(get_db),
):
    record = get_activity_record_by_id(db, current_user.id, record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="活动记录不存在")

    updated = update_activity_record(db, record, get_payload_data(payload))
    return build_activity_record_response(updated)


@router.delete("/{record_id}", response_model=MessageResponse)
def delete_my_activity_record(
    record_id: int,
    current_user: User = Depends(get_activated_user),
    db: Session = Depends(get_db),
):
    record = get_activity_record_by_id(db, current_user.id, record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="活动记录不存在")

    delete_activity_record(db, record)
    return MessageResponse(message="活动记录删除成功")
