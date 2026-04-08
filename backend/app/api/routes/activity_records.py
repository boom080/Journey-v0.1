from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.crud.activity_record import (
    create_activity_record,
    delete_activity_record,
    get_activity_record_by_id,
    list_activity_records,
)
from app.models.activity_record import ActivityRecord
from app.models.user import User
from app.schemas.activity_record import (
    ActivityRecordCreateRequest,
    ActivityRecordResponse,
    MessageResponse,
)

router = APIRouter(prefix="/activity-records", tags=["Activity Records"])


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
    )


def get_payload_data(payload: ActivityRecordCreateRequest) -> dict:
    if hasattr(payload, "model_dump"):
        return payload.model_dump()
    return payload.dict()


@router.get("/", response_model=List[ActivityRecordResponse])
def get_my_activity_records(
    record_date: Optional[date] = Query(default=None),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date 不能大于 end_date",
        )

    records = list_activity_records(
        db=db,
        user_id=current_user.id,
        record_date=record_date,
        start_date=start_date,
        end_date=end_date,
    )
    return [build_activity_record_response(record) for record in records]


@router.post("/", response_model=ActivityRecordResponse)
def create_my_activity_record(
    payload: ActivityRecordCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = create_activity_record(
        db=db,
        user_id=current_user.id,
        data=get_payload_data(payload),
    )
    return build_activity_record_response(record)


@router.delete("/{record_id}", response_model=MessageResponse)
def delete_my_activity_record(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = get_activity_record_by_id(db, current_user.id, record_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="活动记录不存在",
        )

    delete_activity_record(db, record)
    return MessageResponse(message="活动记录删除成功")