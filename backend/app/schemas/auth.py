from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class WechatLoginRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=255)
    nickname: Optional[str] = Field(default=None, max_length=50)
    avatar_url: Optional[str] = Field(default=None, max_length=255)


class InviteVerifyRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=64)


class UserProfilePayload(BaseModel):
    id: int
    openid: str
    unionid: Optional[str] = None
    nickname: str
    avatar_url: Optional[str] = None
    is_activated: bool
    invite_code_id: Optional[int] = None
    goal: str
    height: Optional[float] = None
    weight: Optional[float] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    openid: str
    unionid: Optional[str] = None
    user: UserProfilePayload


class InviteCodePayload(BaseModel):
    id: int
    code: str
    status: str
    max_uses: int
    used_count: int
    used_by_user_id: Optional[int] = None
    used_by_openid: Optional[str] = None
    expires_at: Optional[datetime] = None


class InviteVerifyResponse(BaseModel):
    message: str
    invite_code_id: int
    user: UserProfilePayload
    invite_code: InviteCodePayload
