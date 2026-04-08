from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AICapability(str, Enum):
    FOOD_TEXT_ESTIMATE = "food_text_estimate"
    ACTIVITY_TEXT_ESTIMATE = "activity_text_estimate"
    HOME_SUGGESTION = "home_suggestion"
    FOOD_IMAGE_ANALYSIS = "food_image_analysis"
    ACTIVITY_OCR_ANALYSIS = "activity_ocr_analysis"
    PDF_PARSE = "pdf_parse"
    RAG_KNOWLEDGE_QUERY = "rag_knowledge_query"


class SourceType(str, Enum):
    MANUAL = "manual"
    AI = "ai"
    IMAGE = "image"
    OCR = "ocr"
    PDF = "pdf"
    RAG = "rag"


class AIRequestContext(BaseModel):
    user_id: Optional[int] = None
    nickname: Optional[str] = None
    goal: Optional[str] = None
    record_date: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


class AIResultItem(BaseModel):
    title: str = ""
    name: Optional[str] = None
    detail: str = ""
    meal: Optional[str] = None
    location: Optional[str] = None
    record_date: Optional[str] = None
    kcal: float = 0
    time_text: Optional[str] = None
    source_type: SourceType = SourceType.AI
    ai_type: str
    extra: Dict[str, Any] = Field(default_factory=dict)


class AIResult(BaseModel):
    capability: AICapability
    provider: str = ""
    model: str = ""
    source_type: SourceType = SourceType.AI
    ai_type: str
    items: List[AIResultItem] = Field(default_factory=list)
    total_kcal: float = 0
    summary: str = ""
    extra: Dict[str, Any] = Field(default_factory=dict)


class FoodTextEstimateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)
    record_date: Optional[str] = None
    time_text: Optional[str] = Field(default=None, max_length=20)
    meal: Optional[str] = Field(default=None, max_length=20)
    location: Optional[str] = Field(default=None, max_length=100)
    extra: Dict[str, Any] = Field(default_factory=dict)


class ActivityTextEstimateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)
    record_date: Optional[str] = None
    time_text: Optional[str] = Field(default=None, max_length=20)
    location: Optional[str] = Field(default=None, max_length=100)
    extra: Dict[str, Any] = Field(default_factory=dict)


class HomeSuggestionRequest(BaseModel):
    today_summary: Optional[str] = None
    intake_kcal: Optional[float] = None
    activity_kcal: Optional[float] = None
    net_kcal: Optional[float] = None
    recent_updates: List[Dict[str, Any]] = Field(default_factory=list)
    extra: Dict[str, Any] = Field(default_factory=dict)
