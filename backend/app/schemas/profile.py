from typing import Literal, Optional

from pydantic import BaseModel, Field

GoalType = Literal["减脂", "增肌", "保持体重"]
UnitType = Literal["kg", "lb"]


class ProfileResponse(BaseModel):
    id: int
    user_id: int
    nickname: str
    account: Optional[str] = None
    goal: GoalType
    reminder_enabled: bool
    unit: UnitType
    gender: Optional[str] = None
    age: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    target_weight: Optional[float] = None
    goal_text: Optional[str] = None


class ProfileUpdateRequest(BaseModel):
    nickname: Optional[str] = Field(default=None, min_length=1, max_length=50)
    account: Optional[str] = Field(default=None, max_length=100)
    goal: Optional[GoalType] = None
    reminder_enabled: Optional[bool] = None
    unit: Optional[UnitType] = None
    gender: Optional[str] = Field(default=None, max_length=20)
    age: Optional[int] = Field(default=None, ge=0, le=120)
    height: Optional[float] = Field(default=None, ge=0, le=300)
    weight: Optional[float] = Field(default=None, ge=0, le=500)
    target_weight: Optional[float] = Field(default=None, ge=0, le=500)
    goal_text: Optional[str] = Field(default=None, max_length=500)