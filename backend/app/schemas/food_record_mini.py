from datetime import date
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class FoodRecordCreateRequest(BaseModel):
    record_date: date
    time_text: Optional[str] = Field(default=None, max_length=20)
    meal: str = Field(..., min_length=1, max_length=20)
    detail: str = Field(..., min_length=1, max_length=255)
    location: Optional[str] = Field(default=None, max_length=100)
    kcal: float = Field(..., ge=0, le=10000)
    source_type: str = Field(default="manual", min_length=1, max_length=30)
    ai_type: Optional[str] = Field(default=None, max_length=50)


class FoodRecordUpdateRequest(BaseModel):
    record_date: Optional[date] = None
    time_text: Optional[str] = Field(default=None, max_length=20)
    meal: Optional[str] = Field(default=None, min_length=1, max_length=20)
    detail: Optional[str] = Field(default=None, min_length=1, max_length=255)
    location: Optional[str] = Field(default=None, max_length=100)
    kcal: Optional[float] = Field(default=None, ge=0, le=10000)
    source_type: Optional[str] = Field(default=None, min_length=1, max_length=30)
    ai_type: Optional[str] = Field(default=None, max_length=50)


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
    ai_type: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


class MessageResponse(BaseModel):
    message: str
