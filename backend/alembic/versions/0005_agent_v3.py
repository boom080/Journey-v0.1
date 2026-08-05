"""add Agent v3 checkpoints, observations, and explicit resume metadata

Revision ID: 0005_agent_v3
Revises: 0004_agent_v2
Create Date: 2026-08-04
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_agent_v3"
down_revision: str | Sequence[str] | None = "0004_agent_v2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "agent_runs",
        sa.Column("observations", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
    )
    op.add_column(
        "agent_runs",
        sa.Column("checkpoint", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
    )
    op.add_column(
        "agent_runs", sa.Column("resume_count", sa.Integer(), server_default="0", nullable=False)
    )
    op.add_column(
        "agent_runs", sa.Column("checkpoint_expires_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("agent_confirmations", sa.Column("step_id", sa.String(length=24), nullable=True))


def downgrade() -> None:
    op.drop_column("agent_confirmations", "step_id")
    op.drop_column("agent_runs", "checkpoint_expires_at")
    op.drop_column("agent_runs", "resume_count")
    op.drop_column("agent_runs", "checkpoint")
    op.drop_column("agent_runs", "observations")
