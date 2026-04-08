from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.activity_record import ActivityRecord
from app.models.food_record import FoodRecord
from app.models.user import User
from app.schemas.journey import JourneyDayResponse
from app.services.journey import build_journey_days

router = APIRouter(prefix="/journey-days", tags=["Journey"])


@router.get("/", response_model=List[JourneyDayResponse])
def get_my_journey_days(
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    limit: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date 不能大于 end_date",
        )

    food_query = db.query(FoodRecord).filter(FoodRecord.user_id == current_user.id)
    activity_query = db.query(ActivityRecord).filter(ActivityRecord.user_id == current_user.id)

    if start_date:
        food_query = food_query.filter(FoodRecord.record_date >= start_date)
        activity_query = activity_query.filter(ActivityRecord.record_date >= start_date)

    if end_date:
        food_query = food_query.filter(FoodRecord.record_date <= end_date)
        activity_query = activity_query.filter(ActivityRecord.record_date <= end_date)

    food_records = food_query.order_by(
        FoodRecord.record_date.desc(),
        FoodRecord.created_at.desc(),
    ).all()

    activity_records = activity_query.order_by(
        ActivityRecord.record_date.desc(),
        ActivityRecord.created_at.desc(),
    ).all()

    return build_journey_days(
        food_records=food_records,
        activity_records=activity_records,
        limit=limit,
    )