from sqlalchemy.orm import Session

from app.models.profile import Profile


DEFAULT_NICKNAME = "即刻用户"
DEFAULT_GOAL = "保持体重"
DEFAULT_UNIT = "kg"


def get_profile_by_user_id(db: Session, user_id: int):
    return db.query(Profile).filter(Profile.user_id == user_id).first()


def create_default_profile(db: Session, user_id: int, username: str = ""):
    profile = Profile(
        user_id=user_id,
        nickname=DEFAULT_NICKNAME,
        account=username or None,
        goal=DEFAULT_GOAL,
        reminder_enabled=True,
        unit=DEFAULT_UNIT,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def get_or_create_profile(db: Session, user_id: int, username: str = ""):
    profile = get_profile_by_user_id(db, user_id)
    if profile:
        return profile
    return create_default_profile(db, user_id, username)


def update_profile(db: Session, profile: Profile, update_data: dict):
    for key, value in update_data.items():
        setattr(profile, key, value)

    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile