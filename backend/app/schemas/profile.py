import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.enums import GoalKind, Sex


def validate_timezone(value: str) -> str:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    cleaned = value.strip()
    try:
        ZoneInfo(cleaned)
    except ZoneInfoNotFoundError as error:
        raise ValueError("Unknown IANA timezone") from error
    return cleaned


class ProfileUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=50)
    timezone: str | None = Field(default=None, max_length=64)
    locale: str | None = Field(default=None, min_length=2, max_length=16)
    sex: Sex | None = None
    birth_date: date | None = None
    height_cm: float | None = Field(default=None, ge=80, le=250)
    preferred_unit: str | None = Field(default=None, pattern="^(metric|imperial)$")

    @field_validator("display_name", "locale")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Value cannot be blank")
        return cleaned

    @field_validator("timezone")
    @classmethod
    def known_timezone(cls, value: str | None) -> str | None:
        return validate_timezone(value) if value is not None else None

    @field_validator("birth_date")
    @classmethod
    def sensible_birth_date(cls, value: date | None) -> date | None:
        if value is not None and (value >= date.today() or value.year < 1900):
            raise ValueError("Birth date must be in the past")
        return value

    @model_validator(mode="after")
    def not_empty(self) -> "ProfileUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("At least one profile field is required")
        return self


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    display_name: str
    timezone: str
    locale: str
    sex: str | None
    birth_date: date | None
    height_cm: float | None
    preferred_unit: str
    latest_weight_kg: float | None
    updated_at: datetime


class GoalUpsertRequest(BaseModel):
    kind: GoalKind
    target_weight_kg: float | None = Field(default=None, ge=25, le=400)
    daily_energy_target_kcal: int | None = Field(default=None, ge=800, le=10000)
    starts_on: date = Field(default_factory=date.today)
    target_date: date | None = None

    @model_validator(mode="after")
    def valid_dates(self) -> "GoalUpsertRequest":
        if self.target_date is not None and self.target_date < self.starts_on:
            raise ValueError("Target date cannot be before start date")
        return self


class GoalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: str
    target_weight_kg: float | None
    daily_energy_target_kcal: int | None
    starts_on: date
    target_date: date | None
    is_active: bool
    updated_at: datetime
