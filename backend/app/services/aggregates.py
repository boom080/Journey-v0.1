from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select, union
from sqlalchemy.orm import Session

from app.api.errors import APIError
from app.models.activity_record import ActivityRecord
from app.models.food_record import FoodRecord
from app.models.user import User
from app.models.weight_record import WeightRecord
from app.schemas.aggregates import HomeTodayResponse, JourneyDay, JourneyResponse, RecordCounts
from app.schemas.profile import GoalResponse
from app.schemas.records import ActivityRecordResponse, FoodRecordResponse, WeightRecordResponse
from app.services.energy import estimate_resting_energy
from app.services.profile import get_active_goal


def _sum(values) -> float:
    return round(sum(float(value or 0) for value in values), 2)


def home_today(db: Session, user: User, requested_date: date | None) -> HomeTodayResponse:
    day = requested_date or datetime.now(UTC).astimezone(ZoneInfo(user.profile.timezone)).date()
    food = list(
        db.scalars(
            select(FoodRecord).where(FoodRecord.user_id == user.id, FoodRecord.record_date == day)
        )
    )
    activity = list(
        db.scalars(
            select(ActivityRecord).where(
                ActivityRecord.user_id == user.id, ActivityRecord.record_date == day
            )
        )
    )
    weight = list(
        db.scalars(
            select(WeightRecord)
            .where(WeightRecord.user_id == user.id, WeightRecord.record_date == day)
            .order_by(WeightRecord.measured_at.desc())
        )
    )
    latest_weight = db.scalar(
        select(WeightRecord.weight_kg)
        .where(WeightRecord.user_id == user.id)
        .order_by(WeightRecord.measured_at.desc(), WeightRecord.id.desc())
        .limit(1)
    )
    intake = _sum(item.energy_kcal for item in food)
    burned = _sum(item.energy_kcal for item in activity)
    resting_energy = estimate_resting_energy(
        sex=user.profile.sex,
        birth_date=user.profile.birth_date,
        height_cm=float(user.profile.height_cm) if user.profile.height_cm is not None else None,
        weight_kg=float(latest_weight) if latest_weight is not None else None,
        on_date=day,
    )
    goal = get_active_goal(db, user.id)
    return HomeTodayResponse(
        date=day,
        timezone=user.profile.timezone,
        intake_kcal=intake,
        activity_kcal=burned,
        net_kcal=round(intake - burned, 2),
        resting_energy=resting_energy,
        estimated_energy_balance_kcal=(
            round(intake - burned - resting_energy.kcal_per_day, 2)
            if resting_energy.kcal_per_day is not None
            else None
        ),
        counts=RecordCounts(food=len(food), activity=len(activity), weight=len(weight)),
        latest_weight_kg=float(latest_weight) if latest_weight is not None else None,
        active_goal=GoalResponse.model_validate(goal) if goal else None,
    )


def journey(
    db: Session,
    user: User,
    *,
    start_date: date | None,
    end_date: date | None,
    cursor: date | None,
    limit: int,
) -> JourneyResponse:
    today = datetime.now(UTC).astimezone(ZoneInfo(user.profile.timezone)).date()
    upper = end_date or today
    lower = start_date or (upper - timedelta(days=89))
    if lower > upper:
        raise APIError(
            status_code=422,
            code="invalid_date_range",
            message="start_date cannot be after end_date",
        )
    if (upper - lower).days > 365:
        raise APIError(
            status_code=422,
            code="date_range_too_large",
            message="Journey date range cannot exceed 366 days",
        )

    food_dates = select(FoodRecord.record_date.label("record_date")).where(
        FoodRecord.user_id == user.id,
        FoodRecord.record_date >= lower,
        FoodRecord.record_date <= upper,
    )
    activity_dates = select(ActivityRecord.record_date.label("record_date")).where(
        ActivityRecord.user_id == user.id,
        ActivityRecord.record_date >= lower,
        ActivityRecord.record_date <= upper,
    )
    weight_dates = select(WeightRecord.record_date.label("record_date")).where(
        WeightRecord.user_id == user.id,
        WeightRecord.record_date >= lower,
        WeightRecord.record_date <= upper,
    )
    date_union = union(food_dates, activity_dates, weight_dates).subquery()
    dates_query = select(date_union.c.record_date).distinct()
    if cursor is not None:
        dates_query = dates_query.where(date_union.c.record_date < cursor)
    dates = list(db.scalars(dates_query.order_by(date_union.c.record_date.desc()).limit(limit + 1)))
    has_more = len(dates) > limit
    page_dates = dates[:limit]
    if not page_dates:
        return JourneyResponse(items=[], next_cursor=None, has_more=False)

    food = list(
        db.scalars(
            select(FoodRecord)
            .where(FoodRecord.user_id == user.id, FoodRecord.record_date.in_(page_dates))
            .order_by(FoodRecord.recorded_at.desc())
        )
    )
    activity = list(
        db.scalars(
            select(ActivityRecord)
            .where(ActivityRecord.user_id == user.id, ActivityRecord.record_date.in_(page_dates))
            .order_by(ActivityRecord.recorded_at.desc())
        )
    )
    weight = list(
        db.scalars(
            select(WeightRecord)
            .where(WeightRecord.user_id == user.id, WeightRecord.record_date.in_(page_dates))
            .order_by(WeightRecord.measured_at.desc())
        )
    )
    grouped_food: dict[date, list[FoodRecord]] = defaultdict(list)
    grouped_activity: dict[date, list[ActivityRecord]] = defaultdict(list)
    grouped_weight: dict[date, list[WeightRecord]] = defaultdict(list)
    for item in food:
        grouped_food[item.record_date].append(item)
    for item in activity:
        grouped_activity[item.record_date].append(item)
    for item in weight:
        grouped_weight[item.record_date].append(item)

    days = []
    for day in page_dates:
        day_food = grouped_food[day]
        day_activity = grouped_activity[day]
        intake = _sum(item.energy_kcal for item in day_food)
        burned = _sum(item.energy_kcal for item in day_activity)
        days.append(
            JourneyDay(
                date=day,
                intake_kcal=intake,
                activity_kcal=burned,
                net_kcal=round(intake - burned, 2),
                food_records=[FoodRecordResponse.model_validate(item) for item in day_food],
                activity_records=[
                    ActivityRecordResponse.model_validate(item) for item in day_activity
                ],
                weight_records=[
                    WeightRecordResponse.model_validate(item) for item in grouped_weight[day]
                ],
            )
        )
    return JourneyResponse(
        items=days,
        next_cursor=page_dates[-1] if has_more else None,
        has_more=has_more,
    )
