"""add account-scoped AI period summary cache

Revision ID: 0009_agent_summary_cache
Revises: 0008_agent_privacy
Create Date: 2026-09-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0009_agent_summary_cache"
down_revision: str | Sequence[str] | None = "0008_agent_privacy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_summary_caches",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period_days", sa.Integer(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("statistics", sa.JSON(), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("citations", sa.JSON(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("model", sa.String(length=160), nullable=False),
        sa.Column("fallback_used", sa.Boolean(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "period_days"),
    )
    op.create_index(
        "ix_agent_summary_caches_updated",
        "agent_summary_caches",
        ["updated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_agent_summary_caches_updated", table_name="agent_summary_caches")
    op.drop_table("agent_summary_caches")
