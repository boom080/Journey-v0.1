from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

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
    window_days: int | None = Query(default=None, ge=1, le=90),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JourneyResponse:
    if window_days is not None and start_date is None:
        effective_end = (
            end_date or datetime.now(UTC).astimezone(ZoneInfo(user.profile.timezone)).date()
        )
        start_date = effective_end - timedelta(days=window_days - 1)
    return aggregate_service.journey(
        db, user, start_date=start_date, end_date=end_date, cursor=cursor, limit=limit
    )
