from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class FoodRecordCreateRequest(BaseModel):
    record_date: date
    time_text: Optional[str] = Field(default=None, max_length=20)
    meal: str = Field(..., min_length=1, max_length=20)
    detail: str = Field(..., min_length=1, max_length=255)
    location: Optional[str] = Field(default=None, max_length=100)
    kcal: float = Field(..., ge=0, le=10000)
    source_type: str = Field(default="手填", min_length=1, max_length=30)


class FoodRecordResponse(BaseModel):
    id: int
    user_id: int
    record_date: date
    time_text: Optional[str] = None
    meal: str
    detail: str
    location: Optional[str] = None
    kcal: float
    source_type: str


class MessageResponse(BaseModel):
    message: str