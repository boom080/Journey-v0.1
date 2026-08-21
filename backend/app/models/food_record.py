import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.user import utc_now


class FoodRecord(Base):
    __tablename__ = "food_records"
    __table_args__ = (
        CheckConstraint("energy_kcal >= 0 AND energy_kcal <= 20000", name="ck_food_energy"),
        CheckConstraint("portion_amount IS NULL OR portion_amount > 0", name="ck_food_portion"),
        CheckConstraint(
            "meal_type IN ('breakfast', 'lunch', 'dinner', 'snack', 'other')", name="ck_food_meal"
        ),
        CheckConstraint("source IN ('manual', 'agent', 'image', 'import')", name="ck_food_source"),
        CheckConstraint("version >= 1", name="ck_food_records_version_positive"),
        Index("ix_food_records_user_date", "user_id", "record_date"),
        Index("ix_food_records_user_created", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    meal_type: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)
    portion_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    portion_unit: Mapped[str | None] = mapped_column(String(30))
    energy_kcal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    protein_g: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    carbs_g: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    fat_g: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    source: Mapped[str] = mapped_column(String(20), default="manual", nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(120))
    version: Mapped[int] = mapped_column(
        Integer, default=1, server_default=text("1"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
