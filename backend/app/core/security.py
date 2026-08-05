import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import bcrypt
from jose import JWTError, jwt

from app.core.settings import get_settings

ALGORITHM = "HS256"
TokenType = Literal["access", "refresh"]


@dataclass(frozen=True)
class TokenClaims:
    user_id: uuid.UUID
    session_id: uuid.UUID
    token_id: str
    token_type: TokenType
    expires_at: datetime


def hash_password(password: str) -> str:
    raw = password.encode("utf-8")
    if len(raw) > 72:
        raise ValueError("Password cannot exceed 72 UTF-8 bytes")
    return bcrypt.hashpw(raw, bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except (TypeError, ValueError):
        return False


def create_token(
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    token_type: TokenType,
    expires_at: datetime,
    token_id: str | None = None,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "sid": str(session_id),
        "jti": token_id or secrets.token_urlsafe(24),
        "type": token_type,
        "iat": now,
        "exp": expires_at,
        "iss": "journey-api",
    }
    return jwt.encode(payload, get_settings().secret_key, algorithm=ALGORITHM)


def decode_token(token: str, expected_type: TokenType) -> TokenClaims | None:
    try:
        payload = jwt.decode(
            token,
            get_settings().secret_key,
            algorithms=[ALGORITHM],
            issuer="journey-api",
        )
        if payload.get("type") != expected_type:
            return None
        expires_at = datetime.fromtimestamp(float(payload["exp"]), tz=UTC)
        return TokenClaims(
            user_id=uuid.UUID(payload["sub"]),
            session_id=uuid.UUID(payload["sid"]),
            token_id=str(payload["jti"]),
            token_type=expected_type,
            expires_at=expires_at,
        )
    except (JWTError, KeyError, TypeError, ValueError):
        return None


def refresh_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AgentConfirmationClaims:
    user_id: uuid.UUID
    run_id: uuid.UUID
    candidate_id: uuid.UUID
    kind: str
    expires_at: datetime


def create_agent_confirmation_token(
    *,
    user_id: uuid.UUID,
    run_id: uuid.UUID,
    candidate_id: uuid.UUID,
    kind: str,
    expires_at: datetime,
) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user_id),
            "run": str(run_id),
            "candidate": str(candidate_id),
            "kind": kind,
            "type": "agent_confirmation",
            "iat": now,
            "exp": expires_at,
            "iss": "journey-api",
        },
        get_settings().secret_key,
        algorithm=ALGORITHM,
    )


def decode_agent_confirmation_token(token: str) -> AgentConfirmationClaims | None:
    try:
        payload = jwt.decode(
            token,
            get_settings().secret_key,
            algorithms=[ALGORITHM],
            issuer="journey-api",
        )
        if payload.get("type") != "agent_confirmation":
            return None
        return AgentConfirmationClaims(
            user_id=uuid.UUID(payload["sub"]),
            run_id=uuid.UUID(payload["run"]),
            candidate_id=uuid.UUID(payload["candidate"]),
            kind=str(payload["kind"]),
            expires_at=datetime.fromtimestamp(float(payload["exp"]), tz=UTC),
        )
    except (JWTError, KeyError, TypeError, ValueError):
        return None


def token_expirations() -> tuple[datetime, datetime]:
    settings = get_settings()
    now = datetime.now(UTC)
    return (
        now + timedelta(minutes=settings.access_token_minutes),
        now + timedelta(days=settings.refresh_token_days),
    )
