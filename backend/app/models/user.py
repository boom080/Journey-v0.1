from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String

from app.core.database import Base


def now_utc():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    openid = Column(String(100), unique=True, index=True, nullable=False)
    unionid = Column(String(100), nullable=True, index=True)
    nickname = Column(String(50), nullable=False, default="Journey 用户")
    avatar_url = Column(String(255), nullable=True)
    is_activated = Column(Boolean, nullable=False, default=False)
    invite_code_id = Column(Integer, ForeignKey("invite_codes.id"), nullable=True, index=True)
    goal = Column(String(20), nullable=False, default="维持")
    height = Column(Float, nullable=True)
    weight = Column(Float, nullable=True)
    created_at = Column(DateTime, default=now_utc, nullable=False)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc, nullable=False)
