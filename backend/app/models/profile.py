from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text

from app.core.database import Base


def now_utc():
    return datetime.now(timezone.utc)


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)

    nickname = Column(String(50), nullable=False, default="即刻用户")
    account = Column(String(100), nullable=True)
    goal = Column(String(20), nullable=False, default="保持体重")
    reminder_enabled = Column(Boolean, nullable=False, default=True)
    unit = Column(String(10), nullable=False, default="kg")

    gender = Column(String(20), nullable=True)
    age = Column(Integer, nullable=True)
    height = Column(Float, nullable=True)
    weight = Column(Float, nullable=True)
    target_weight = Column(Float, nullable=True)
    goal_text = Column(Text, nullable=True)

    created_at = Column(DateTime, default=now_utc, nullable=False)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc, nullable=False)