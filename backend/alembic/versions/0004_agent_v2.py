"""add Agent v2 threads, plans, verification, and bounded replan metadata

Revision ID: 0004_agent_v2
Revises: 0003_agent_rag
Create Date: 2026-08-03
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_agent_v2"
down_revision: str | Sequence[str] | None = "0003_agent_rag"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_threads",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("memory", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column(
            "memory_version",
            sa.String(length=40),
            server_default="journey-thread-memory-1",
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_threads_user_updated", "agent_threads", ["user_id", "updated_at"])
    op.add_column("agent_runs", sa.Column("thread_id", sa.UUID(), nullable=True))
    op.add_column(
        "agent_runs",
        sa.Column("plan", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
    )
    op.add_column(
        "agent_runs",
        sa.Column("verification", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
    )
    op.add_column(
        "agent_runs",
        sa.Column("replan_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_foreign_key(
        "fk_agent_runs_thread_id_agent_threads",
        "agent_runs",
        "agent_threads",
        ["thread_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_agent_runs_thread_id", "agent_runs", ["thread_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_runs_thread_id", table_name="agent_runs")
    op.drop_constraint("fk_agent_runs_thread_id_agent_threads", "agent_runs", type_="foreignkey")
    op.drop_column("agent_runs", "replan_count")
    op.drop_column("agent_runs", "verification")
    op.drop_column("agent_runs", "plan")
    op.drop_column("agent_runs", "thread_id")
    op.drop_index("ix_agent_threads_user_updated", table_name="agent_threads")
    op.drop_table("agent_threads")
