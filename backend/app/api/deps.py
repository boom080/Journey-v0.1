from dataclasses import dataclass

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import APIError
from app.core.database import get_db
from app.core.security import TokenClaims, decode_token
from app.models.auth_session import AuthSession
from app.models.user import User

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentAuth:
    user: User
    session: AuthSession
    claims: TokenClaims


def get_current_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> CurrentAuth:
    if credentials is None:
        raise APIError(
            status_code=401, code="authentication_required", message="Authentication required"
        )
    claims = decode_token(credentials.credentials, "access")
    if claims is None:
        raise APIError(
            status_code=401, code="invalid_token", message="Access token is invalid or expired"
        )

    session = db.scalar(
        select(AuthSession).where(
            AuthSession.id == claims.session_id,
            AuthSession.user_id == claims.user_id,
        )
    )
    user = db.get(User, claims.user_id)
    if session is None or session.revoked_at is not None or user is None or user.status != "active":
        raise APIError(
            status_code=401, code="invalid_session", message="Session is no longer active"
        )
    return CurrentAuth(user=user, session=session, claims=claims)


def get_current_user(auth: CurrentAuth = Depends(get_current_auth)) -> User:
    return auth.user


def get_request_id(request: Request) -> str:
    return request.state.request_id
