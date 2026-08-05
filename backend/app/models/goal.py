import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.user import utc_now


class Goal(Base):
    __tablename__ = "goals"
    __table_args__ = (
        CheckConstraint("kind IN ('lose_fat', 'gain_muscle', 'maintain')", name="ck_goals_kind"),
        CheckConstraint(
            "target_weight_kg IS NULL OR (target_weight_kg >= 25 AND target_weight_kg <= 400)",
            name="ck_goals_target_weight",
        ),
        CheckConstraint(
            "daily_energy_target_kcal IS NULL OR "
            "(daily_energy_target_kcal >= 800 AND daily_energy_target_kcal <= 10000)",
            name="ck_goals_daily_energy",
        ),
        Index("ix_goals_user_active", "user_id", "is_active"),
        Index("uq_goals_one_active", "user_id", unique=True, postgresql_where=text("is_active")),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    target_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    daily_energy_target_kcal: Mapped[int | None] = mapped_column(Integer)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    target_date: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
