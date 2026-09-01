import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AgentConsent(Base):
    __tablename__ = "agent_consents"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AgentDeletedCost(Base):
    """Unlinked daily cost only: no user, input, run or model identifiers."""

    __tablename__ = "agent_deleted_costs"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 8), nullable=False)
