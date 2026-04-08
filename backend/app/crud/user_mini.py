from typing import Optional

from sqlalchemy.orm import Session

from app.models.user import User


def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_openid(db: Session, openid: str):
    return db.query(User).filter(User.openid == openid).first()


def create_user_by_openid(
    db: Session,
    openid: str,
    unionid: Optional[str] = None,
    nickname: Optional[str] = None,
    avatar_url: Optional[str] = None,
):
    user = User(
        openid=openid,
        unionid=unionid,
        nickname=nickname or "Journey 用户",
        avatar_url=avatar_url,
        is_activated=False,
        goal="维持",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user: User, update_data: dict):
    for key, value in update_data.items():
        setattr(user, key, value)

    db.add(user)
    db.commit()
    db.refresh(user)
    return user
