from datetime import date
from typing import List, Optional

from pydantic import BaseModel


class JourneyFoodItem(BaseModel):
    id: int
    meal: str
    detail: str
    location: str
    kcal: str
    time: Optional[str] = None


class JourneyActivityItem(BaseModel):
    id: int
    name: str
    location: str
    kcal: str
    time: Optional[str] = None


class JourneyDayResponse(BaseModel):
    id: str
    record_date: date
    date: str
    weekday: str

    statusText: str
    statusType: str
    summary: str
    mascotType: str

    intakeKcal: float
    activityKcal: float
    calorieBalance: float

    foodItems: List[JourneyFoodItem]
    activityItems: List[JourneyActivityItem]