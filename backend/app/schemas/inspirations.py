import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InspirationPreviewRequest(BaseModel):
    source_url: str = Field(min_length=12, max_length=2048)


class InspirationPreviewResponse(BaseModel):
    status: Literal["preview", "manual_required"]
    source_url: str
    source_name: Literal["小红书"] = "小红书"
    title: str | None = None
    summary: str | None = None
    source_checked_at: datetime
    safety_flags: list[str]
    message: str


class InspirationCreateRequest(BaseModel):
    source_url: str = Field(min_length=12, max_length=2048)
    title: str = Field(min_length=1, max_length=160)
    summary: str | None = Field(default=None, max_length=500)
    tags: list[str] = Field(default_factory=list, max_length=5)
    source_checked_at: datetime
    confirmed: Literal[True]

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("Title cannot be blank")
        return cleaned

    @field_validator("summary")
    @classmethod
    def strip_summary(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return " ".join(value.split()) or None

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        result: list[str] = []
        for item in value:
            cleaned = " ".join(item.split())
            if not cleaned or len(cleaned) > 24:
                raise ValueError("Each tag must contain 1-24 characters")
            if cleaned not in result:
                result.append(cleaned)
        return result


class InspirationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_url: str
    source_name: str
    title: str
    summary: str | None
    tags: list[str]
    evidence_level: Literal["inspiration_only"]
    source_checked_at: datetime
    created_at: datetime
    updated_at: datetime
