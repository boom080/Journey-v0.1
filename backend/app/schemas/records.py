import uuid
from datetime import date, datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import ActivityIntensity, MealType, RecordSource


class FoodRecordCreate(BaseModel):
    recorded_at: AwareDatetime
    meal_type: MealType
    name: str = Field(min_length=1, max_length=120)
    detail: str | None = Field(default=None, max_length=2000)
    portion_amount: float | None = Field(default=None, gt=0, le=100000)
    portion_unit: str | None = Field(default=None, max_length=30)
    energy_kcal: float = Field(ge=0, le=20000)
    protein_g: float | None = Field(default=None, ge=0, le=5000)
    carbs_g: float | None = Field(default=None, ge=0, le=5000)
    fat_g: float | None = Field(default=None, ge=0, le=5000)
    source: RecordSource = RecordSource.MANUAL
    source_ref: str | None = Field(default=None, max_length=120)


class FoodRecordUpdate(BaseModel):
    recorded_at: AwareDatetime | None = None
    meal_type: MealType | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)
    detail: str | None = Field(default=None, max_length=2000)
    portion_amount: float | None = Field(default=None, gt=0, le=100000)
    portion_unit: str | None = Field(default=None, max_length=30)
    energy_kcal: float | None = Field(default=None, ge=0, le=20000)
    protein_g: float | None = Field(default=None, ge=0, le=5000)
    carbs_g: float | None = Field(default=None, ge=0, le=5000)
    fat_g: float | None = Field(default=None, ge=0, le=5000)

    @model_validator(mode="after")
    def not_empty(self) -> "FoodRecordUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        return self


class FoodRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    recorded_at: datetime
    record_date: date
    meal_type: str
    name: str
    detail: str | None
    portion_amount: float | None
    portion_unit: str | None
    energy_kcal: float
    protein_g: float | None
    carbs_g: float | None
    fat_g: float | None
    source: str
    source_ref: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class ActivityRecordCreate(BaseModel):
    recorded_at: AwareDatetime
    name: str = Field(min_length=1, max_length=120)
    activity_type: str | None = Field(default=None, max_length=60)
    duration_minutes: int = Field(gt=0, le=1440)
    intensity: ActivityIntensity
    energy_kcal: float = Field(ge=0, le=20000)
    note: str | None = Field(default=None, max_length=2000)
    source: RecordSource = RecordSource.MANUAL
    source_ref: str | None = Field(default=None, max_length=120)


class ActivityRecordUpdate(BaseModel):
    recorded_at: AwareDatetime | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)
    activity_type: str | None = Field(default=None, max_length=60)
    duration_minutes: int | None = Field(default=None, gt=0, le=1440)
    intensity: ActivityIntensity | None = None
    energy_kcal: float | None = Field(default=None, ge=0, le=20000)
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def not_empty(self) -> "ActivityRecordUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        return self


class ActivityRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    recorded_at: datetime
    record_date: date
    name: str
    activity_type: str | None
    duration_minutes: int
    intensity: str
    energy_kcal: float
    note: str | None
    source: str
    source_ref: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class WeightRecordCreate(BaseModel):
    measured_at: AwareDatetime
    weight_kg: float = Field(ge=25, le=400)
    note: str | None = Field(default=None, max_length=2000)
    source: RecordSource = RecordSource.MANUAL


class WeightRecordUpdate(BaseModel):
    measured_at: AwareDatetime | None = None
    weight_kg: float | None = Field(default=None, ge=25, le=400)
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def not_empty(self) -> "WeightRecordUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        return self


class WeightRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    measured_at: datetime
    record_date: date
    weight_kg: float
    note: str | None
    source: str
    version: int
    created_at: datetime
    updated_at: datetime
