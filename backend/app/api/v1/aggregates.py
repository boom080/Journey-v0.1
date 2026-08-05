from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.aggregates import HomeTodayResponse, JourneyResponse
from app.services import aggregates as aggregate_service

router = APIRouter(tags=["Aggregates"])


@router.get("/home/today", response_model=HomeTodayResponse)
def home_today(
    day: date | None = Query(default=None, alias="date"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HomeTodayResponse:
    return aggregate_service.home_today(db, user, day)


@router.get("/journey", response_model=JourneyResponse)
def journey(
    start_date: date | None = None,
    end_date: date | None = None,
    cursor: date | None = None,
    limit: int = Query(default=7, ge=1, le=31),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JourneyResponse:
    return aggregate_service.journey(
        db, user, start_date=start_date, end_date=end_date, cursor=cursor, limit=limit
    )
