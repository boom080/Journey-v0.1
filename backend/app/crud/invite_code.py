from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.invite_code import InviteCode


def now_utc():
    return datetime.now(timezone.utc)


def get_invite_code_by_code(db: Session, code: str):
    return (
        db.query(InviteCode)
        .filter(InviteCode.code == code.strip())
        .first()
    )


def list_invite_codes(db: Session):
    return (
        db.query(InviteCode)
        .order_by(InviteCode.id.asc(), InviteCode.created_at.asc())
        .all()
    )


def invite_code_is_expired(invite_code: InviteCode) -> bool:
    if not invite_code.expires_at:
        return False

    expires_at = invite_code.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    return expires_at < now_utc()


def get_invite_code_effective_status(invite_code: InviteCode) -> str:
    if invite_code.status == "disabled":
        return "disabled"

    if invite_code_is_expired(invite_code):
        return "expired"

    if int(invite_code.used_count or 0) >= max(int(invite_code.max_uses or 1), 1):
        return "used"

    return "unused"


def create_invite_code(
    db: Session,
    code: str,
    *,
    max_uses: int = 1,
    expires_at=None,
    status: str = "unused",
):
    normalized_code = code.strip()
    if not normalized_code:
        raise ValueError("Invite code cannot be empty")

    existing = get_invite_code_by_code(db, normalized_code)
    if existing:
        raise ValueError(f"Invite code already exists: {normalized_code}")

    invite_code = InviteCode(
        code=normalized_code,
        status=status,
        max_uses=max(int(max_uses or 1), 1),
        used_count=0,
        expires_at=expires_at,
    )
    db.add(invite_code)
    db.commit()
    db.refresh(invite_code)
    return invite_code


def update_invite_code_status(db: Session, invite_code: InviteCode, status: str):
    invite_code.status = status
    db.add(invite_code)
    db.commit()
    db.refresh(invite_code)
    return invite_code


def mark_invite_code_used(db: Session, invite_code: InviteCode, user_id: int, openid: str):
    invite_code.used_count = int(invite_code.used_count or 0) + 1
    invite_code.used_by_user_id = user_id
    invite_code.used_by_openid = openid
    invite_code.status = "used" if invite_code.used_count >= max(int(invite_code.max_uses or 1), 1) else "unused"
    db.add(invite_code)
    db.commit()
    db.refresh(invite_code)
    return invite_code
