import uuid
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.agent import AgentUsage, FoodAgentCandidate

FoodImageScaleReferenceType = Literal[
    "none",
    "journey_card",
    "plate_diameter",
    "bowl_diameter",
]


class FoodImageAnalyzeRequest(BaseModel):
    image_base64: str = Field(min_length=16, max_length=7_100_000)
    media_type: Literal["image/jpeg", "image/png", "image/webp"]
    width: int = Field(gt=0, le=20_000)
    height: int = Field(gt=0, le=20_000)
    meal_type_hint: Literal["breakfast", "lunch", "dinner", "snack", "other"] = "other"
    note: str | None = Field(default=None, max_length=200)
    scale_reference_type: FoodImageScaleReferenceType = "none"
    scale_reference_size_cm: float | None = Field(default=None, ge=8, le=60)
    confirm_upload: Literal[True]

    @model_validator(mode="after")
    def validate_scale_reference(self) -> "FoodImageAnalyzeRequest":
        needs_size = self.scale_reference_type in {"plate_diameter", "bowl_diameter"}
        if needs_size and self.scale_reference_size_cm is None:
            raise ValueError("Plate and bowl references require a diameter in centimeters")
        if not needs_size and self.scale_reference_size_cm is not None:
            raise ValueError("Only plate and bowl references accept a custom diameter")
        return self


class FoodImageItem(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    canonical_name_en: str | None = Field(default=None, max_length=120)
    portion_amount: float | None = Field(default=None, gt=0, le=100_000)
    portion_unit: str | None = Field(default=None, max_length=30)
    energy_kcal: float | None = Field(default=None, ge=0, le=20_000)


class FoodImageEstimate(BaseModel):
    is_food: bool
    name: str | None = Field(default=None, max_length=120)
    canonical_name_en: str | None = Field(default=None, max_length=120)
    items: list[FoodImageItem] = Field(default_factory=list, max_length=8)
    meal_type: Literal["breakfast", "lunch", "dinner", "snack", "other"] = "other"
    portion_amount: float | None = Field(default=None, gt=0, le=100_000)
    portion_unit: str | None = Field(default=None, max_length=30)
    energy_kcal: float | None = Field(default=None, ge=0, le=20_000)
    energy_min_kcal: float | None = Field(default=None, ge=0, le=20_000)
    energy_max_kcal: float | None = Field(default=None, ge=0, le=20_000)
    confidence: Literal["low", "medium"]
    assumptions: list[str] = Field(default_factory=list, max_length=5)
    scale_reference_used: bool = False
    needs_user_correction: Literal[True] = True

    @model_validator(mode="after")
    def validate_estimate(self) -> "FoodImageEstimate":
        if not self.is_food:
            return self
        required = (
            self.name,
            self.energy_kcal,
            self.energy_min_kcal,
            self.energy_max_kcal,
        )
        if any(value is None for value in required) or not self.items:
            raise ValueError("Food estimates require a name, items, and energy range")
        if not (
            self.energy_min_kcal <= self.energy_kcal <= self.energy_max_kcal  # type: ignore[operator]
        ):
            raise ValueError("energy_kcal must be within the uncertainty range")
        return self


class FoodImageAnalysisResponse(BaseModel):
    analysis_id: uuid.UUID
    status: Literal["candidate", "manual_required"]
    candidate: FoodAgentCandidate | None = None
    estimate: FoodImageEstimate | None = None
    message: str
    fallback_used: bool
    image_retained: Literal[False] = False
    usage: AgentUsage
