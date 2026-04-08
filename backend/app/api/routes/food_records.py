from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.crud.food_record import (
    create_food_record,
    delete_food_record,
    get_food_record_by_id,
    list_food_records,
)
from app.models.food_record import FoodRecord
from app.models.user import User
from app.schemas.food_record import (
    FoodRecordCreateRequest,
    FoodRecordResponse,
    MessageResponse,
)

router = APIRouter(prefix="/food-records", tags=["Food Records"])


def build_food_record_response(record: FoodRecord) -> FoodRecordResponse:
    return FoodRecordResponse(
        id=record.id,
        user_id=record.user_id,
        record_date=record.record_date,
        time_text=record.time_text,
        meal=record.meal,
        detail=record.detail,
        location=record.location,
        kcal=record.kcal,
        source_type=record.source_type,
    )


def get_payload_data(payload: FoodRecordCreateRequest) -> dict:
    if hasattr(payload, "model_dump"):
        return payload.model_dump()
    return payload.dict()


@router.get("/", response_model=List[FoodRecordResponse])
def get_my_food_records(
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

    records = list_food_records(
        db=db,
        user_id=current_user.id,
        record_date=record_date,
        start_date=start_date,
        end_date=end_date,
    )
    return [build_food_record_response(record) for record in records]


@router.post("/", response_model=FoodRecordResponse)
def create_my_food_record(
    payload: FoodRecordCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = create_food_record(
        db=db,
        user_id=current_user.id,
        data=get_payload_data(payload),
    )
    return build_food_record_response(record)


@router.delete("/{record_id}", response_model=MessageResponse)
def delete_my_food_record(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = get_food_record_by_id(db, current_user.id, record_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="饮食记录不存在",
        )

    delete_food_record(db, record)
    return MessageResponse(message="饮食记录删除成功")