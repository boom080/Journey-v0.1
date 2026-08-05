import uuid
from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
    request_id: str


class MessageResponse(BaseModel):
    message: str


class PageMeta(BaseModel):
    limit: int
    offset: int
    total: int


class Page[T](BaseModel):
    items: list[T]
    meta: PageMeta


class ResourceId(BaseModel):
    id: uuid.UUID


class AuditContext(BaseModel):
    request_id: str = Field(min_length=1, max_length=128)
