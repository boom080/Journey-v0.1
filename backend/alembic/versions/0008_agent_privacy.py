"""Persist versioned, account-scoped external text model consent."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0008_agent_privacy"
down_revision = "0007_life_inspirations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_deleted_costs",
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("cost_usd", sa.Numeric(12, 8), nullable=False),
    )
    op.create_table(
        "agent_consents",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_version", sa.String(64), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("agent_consents")
    op.drop_table("agent_deleted_costs")
