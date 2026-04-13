from typing import Literal, Optional

from pydantic import BaseModel, Field

GoalType = Literal["减脂", "维持", "增肌"]
GenderType = Literal["male", "female"]


class ProfileResponse(BaseModel):
    id: int
    openid: str
    nickname: str
    goal: GoalType
    gender: Optional[GenderType] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    body_fat_rate: Optional[float] = None
    avatar_url: Optional[str] = None
    is_activated: bool


class ProfileUpdateRequest(BaseModel):
    nickname: Optional[str] = Field(default=None, min_length=1, max_length=50)
    goal: Optional[GoalType] = None
    gender: Optional[GenderType] = None
    height: Optional[float] = Field(default=None, ge=0, le=300)
    weight: Optional[float] = Field(default=None, ge=0, le=500)
    body_fat_rate: Optional[float] = Field(default=None, ge=0, le=70)
