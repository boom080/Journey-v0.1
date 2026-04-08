from datetime import date
from typing import List, Optional

from pydantic import BaseModel


class JourneyFoodItem(BaseModel):
    id: int
    meal: str
    detail: str
    location: str
    kcal: float
    time_text: Optional[str] = None


class JourneyActivityItem(BaseModel):
    id: int
    name: str
    location: str
    kcal: float
    time_text: Optional[str] = None


class JourneyDayResponse(BaseModel):
    id: str
    record_date: date
    summary: str
    status_text: str
    foodItems: List[JourneyFoodItem]
    activityItems: List[JourneyActivityItem]


class JourneyListResponse(BaseModel):
    items: List[JourneyDayResponse]
    next_cursor: Optional[str] = None
    has_more: bool
