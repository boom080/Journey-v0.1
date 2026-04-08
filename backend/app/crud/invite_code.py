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


def invite_code_is_expired(invite_code: InviteCode) -> bool:
    if not invite_code.expires_at:
        return False

    expires_at = invite_code.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    return expires_at < now_utc()


def mark_invite_code_used(db: Session, invite_code: InviteCode, user_id: int, openid: str):
    invite_code.used_count = int(invite_code.used_count or 0) + 1
    invite_code.used_by_user_id = user_id
    invite_code.used_by_openid = openid
    invite_code.status = "used" if invite_code.used_count >= max(int(invite_code.max_uses or 1), 1) else "unused"
    db.add(invite_code)
    db.commit()
    db.refresh(invite_code)
    return invite_code
