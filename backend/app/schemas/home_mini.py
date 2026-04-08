from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class HomeUpdateItem(BaseModel):
    title: str
    description: str
    time_text: Optional[str] = None
    kcal: Optional[str] = None


class HomeSummaryResponse(BaseModel):
    today_date: str
    today_summary: str
    goal_suggestion: str
    intake_kcal: float
    activity_kcal: float
    net_kcal: float
    recent_updates: List[HomeUpdateItem]
    extra: Dict[str, Any] = Field(default_factory=dict)
