import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.errors import APIError
from app.core.security import (
    create_token,
    decode_token,
    hash_password,
    refresh_token_hash,
    token_expirations,
    verify_password,
)
from app.domain.enums import IdentityKind
from app.domain.identity import normalize_email, normalize_username
from app.models.audit import AuditEvent
from app.models.auth_session import AuthSession
from app.models.profile import Profile
from app.models.user import Identity, PasswordCredential, User
from app.repositories.users import get_user_by_identifier, identity_exists
from app.schemas.auth import RegisterRequest, TokenResponse, UserResponse

MAX_FAILED_ATTEMPTS = 5
LOCK_MINUTES = 5
DUMMY_PASSWORD_HASH = hash_password("JourneyDummyPassword2026")


def user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        status=user.status,
        identities=sorted(user.identities, key=lambda item: item.kind),
        created_at=user.created_at,
    )


def _audit(db: Session, user_id: uuid.UUID | None, action: str, request_id: str) -> None:
    db.add(
        AuditEvent(
            user_id=user_id,
            action=action,
            resource_type="auth",
            resource_id=str(user_id) if user_id else None,
            request_id=request_id,
        )
    )


def create_user(db: Session, payload: RegisterRequest) -> User:
    email = normalize_email(payload.email)
    username = normalize_username(payload.username)
    if identity_exists(db, IdentityKind.EMAIL, email):
        raise APIError(status_code=409, code="email_taken", message="Email is already registered")
    if identity_exists(db, IdentityKind.USERNAME, username):
        raise APIError(
            status_code=409, code="username_taken", message="Username is already registered"
        )

    user = User()
    user.identities = [
        Identity(
            kind=IdentityKind.EMAIL,
            normalized_value=email,
            display_value=payload.email.strip(),
            is_verified=False,
        ),
        Identity(
            kind=IdentityKind.USERNAME,
            normalized_value=username,
            display_value=payload.username.strip(),
            is_verified=True,
        ),
    ]
    user.credential = PasswordCredential(password_hash=hash_password(payload.password))
    user.profile = Profile(display_name=payload.display_name)
    db.add(user)
    try:
        db.flush()
    except IntegrityError as error:
        db.rollback()
        raise APIError(
            status_code=409,
            code="identity_taken",
            message="Email or username is already registered",
        ) from error
    return user


def _issue_tokens(
    db: Session, user: User, existing_session: AuthSession | None = None
) -> TokenResponse:
    access_exp, refresh_exp = token_expirations()
    session = existing_session or AuthSession(
        user_id=user.id,
        refresh_token_hash="pending",
        expires_at=refresh_exp,
    )
    if existing_session is None:
        db.add(session)
        db.flush()
    refresh = create_token(
        user_id=user.id,
        session_id=session.id,
        token_type="refresh",
        expires_at=refresh_exp,
    )
    access = create_token(
        user_id=user.id,
        session_id=session.id,
        token_type="access",
        expires_at=access_exp,
    )
    session.refresh_token_hash = refresh_token_hash(refresh)
    session.expires_at = refresh_exp
    session.last_used_at = datetime.now(UTC) if existing_session else None
    return TokenResponse(
        access_token=access,
        access_expires_at=access_exp,
        refresh_token=refresh,
        refresh_expires_at=refresh_exp,
        user=user_response(user),
    )


def register(db: Session, payload: RegisterRequest, request_id: str) -> TokenResponse:
    user = create_user(db, payload)
    response = _issue_tokens(db, user)
    _audit(db, user.id, "auth.register", request_id)
    db.commit()
    return response


def login(db: Session, identifier: str, password: str, request_id: str) -> TokenResponse:
    user = get_user_by_identifier(db, identifier)
    credential = user.credential if user is not None else None
    now = datetime.now(UTC)
    if (
        credential is not None
        and credential.locked_until is not None
        and credential.locked_until > now
    ):
        raise APIError(
            status_code=429,
            code="account_locked",
            message="Too many failed attempts; try again later",
        )

    valid = verify_password(
        password, credential.password_hash if credential else DUMMY_PASSWORD_HASH
    )
    if user is None or credential is None or not valid or user.status != "active":
        if credential is not None:
            credential.failed_attempts += 1
            if credential.failed_attempts >= MAX_FAILED_ATTEMPTS:
                credential.locked_until = now + timedelta(minutes=LOCK_MINUTES)
                credential.failed_attempts = 0
            _audit(db, user.id if user else None, "auth.login_failed", request_id)
            db.commit()
        raise APIError(
            status_code=401, code="invalid_credentials", message="Invalid login credentials"
        )

    credential.failed_attempts = 0
    credential.locked_until = None
    response = _issue_tokens(db, user)
    _audit(db, user.id, "auth.login", request_id)
    db.commit()
    return response


def refresh(db: Session, token: str, request_id: str) -> TokenResponse:
    claims = decode_token(token, "refresh")
    if claims is None:
        raise APIError(
            status_code=401,
            code="invalid_refresh_token",
            message="Refresh token is invalid or expired",
        )
    session = db.scalar(
        select(AuthSession).where(AuthSession.id == claims.session_id).with_for_update()
    )
    user = db.scalar(
        select(User)
        .where(User.id == claims.user_id)
        .options(selectinload(User.identities), selectinload(User.credential))
    )
    now = datetime.now(UTC)
    if (
        session is None
        or user is None
        or session.user_id != user.id
        or session.revoked_at is not None
        or session.expires_at <= now
        or user.status != "active"
    ):
        raise APIError(
            status_code=401, code="invalid_session", message="Refresh session is no longer active"
        )
    if not secrets.compare_digest(session.refresh_token_hash, refresh_token_hash(token)):
        session.revoked_at = now
        _audit(db, user.id, "auth.refresh_reuse", request_id)
        db.commit()
        raise APIError(
            status_code=401,
            code="refresh_token_reused",
            message="Refresh token has already been rotated",
        )

    response = _issue_tokens(db, user, existing_session=session)
    _audit(db, user.id, "auth.refresh", request_id)
    db.commit()
    return response


def logout(db: Session, session: AuthSession, user: User, request_id: str) -> None:
    if session.revoked_at is None:
        session.revoked_at = datetime.now(UTC)
        _audit(db, user.id, "auth.logout", request_id)
        db.commit()
