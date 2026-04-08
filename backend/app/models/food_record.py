from datetime import datetime, timezone

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String

from app.core.database import Base


def now_utc():
    return datetime.now(timezone.utc)


class FoodRecord(Base):
    __tablename__ = "food_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    record_date = Column(Date, nullable=False, index=True)
    time_text = Column(String(20), nullable=True)
    meal = Column(String(20), nullable=False)
    detail = Column(String(255), nullable=False)
    location = Column(String(100), nullable=True)
    kcal = Column(Float, nullable=False)
    source_type = Column(String(30), nullable=False, default="manual")
    ai_type = Column(String(50), nullable=True)

    created_at = Column(DateTime, default=now_utc, nullable=False)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc, nullable=False)
