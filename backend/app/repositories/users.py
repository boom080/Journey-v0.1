from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.enums import IdentityKind
from app.domain.identity import normalize_email, normalize_username
from app.models.user import Identity, User


def identity_parts(identifier: str) -> tuple[str, str] | None:
    try:
        if "@" in identifier:
            return IdentityKind.EMAIL.value, normalize_email(identifier)
        return IdentityKind.USERNAME.value, normalize_username(identifier)
    except ValueError:
        return None


def get_user_by_identifier(db: Session, identifier: str) -> User | None:
    parts = identity_parts(identifier)
    if parts is None:
        return None
    kind, normalized = parts
    return db.scalar(
        select(User)
        .join(Identity)
        .where(Identity.kind == kind, Identity.normalized_value == normalized)
        .options(
            selectinload(User.identities), selectinload(User.credential), selectinload(User.profile)
        )
    )


def identity_exists(db: Session, kind: str, normalized_value: str) -> bool:
    return (
        db.scalar(
            select(Identity.id).where(
                Identity.kind == kind,
                Identity.normalized_value == normalized_value,
            )
        )
        is not None
    )
