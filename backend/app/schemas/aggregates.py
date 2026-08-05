from datetime import date

from pydantic import BaseModel

from app.schemas.profile import GoalResponse
from app.schemas.records import ActivityRecordResponse, FoodRecordResponse, WeightRecordResponse


class RecordCounts(BaseModel):
    food: int
    activity: int
    weight: int


class HomeTodayResponse(BaseModel):
    date: date
    timezone: str
    intake_kcal: float
    activity_kcal: float
    net_kcal: float
    counts: RecordCounts
    latest_weight_kg: float | None
    active_goal: GoalResponse | None


class JourneyDay(BaseModel):
    date: date
    intake_kcal: float
    activity_kcal: float
    net_kcal: float
    food_records: list[FoodRecordResponse]
    activity_records: list[ActivityRecordResponse]
    weight_records: list[WeightRecordResponse]


class JourneyResponse(BaseModel):
    items: list[JourneyDay]
    next_cursor: date | None
    has_more: bool
