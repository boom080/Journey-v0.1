import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.identity import normalize_email, normalize_username, validate_password


class RegisterRequest(BaseModel):
    email: str = Field(max_length=254)
    username: str = Field(max_length=32)
    password: str
    display_name: str = Field(min_length=1, max_length=50)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("username")
    @classmethod
    def valid_username(cls, value: str) -> str:
        return normalize_username(value)

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return validate_password(value)

    @field_validator("display_name")
    @classmethod
    def clean_display_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Display name cannot be blank")
        return cleaned


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=32)


class IdentityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    kind: str
    display_value: str
    is_verified: bool


class UserResponse(BaseModel):
    id: uuid.UUID
    status: str
    identities: list[IdentityResponse]
    created_at: datetime


class TokenResponse(BaseModel):
    token_type: str = "bearer"
    access_token: str
    access_expires_at: datetime
    refresh_token: str
    refresh_expires_at: datetime
    user: UserResponse
