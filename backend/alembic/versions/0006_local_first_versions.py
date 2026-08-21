"""add optimistic versions for local-first synchronization

Revision ID: 0006_local_first
Revises: 0005_agent_v3
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_local_first"
down_revision: str | Sequence[str] | None = "0005_agent_v3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VERSIONED_TABLES = (
    "profiles",
    "goals",
    "food_records",
    "activity_records",
    "weight_records",
)


def upgrade() -> None:
    for table_name in VERSIONED_TABLES:
        op.add_column(
            table_name,
            sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        )
        op.create_check_constraint(
            f"ck_{table_name}_version_positive",
            table_name,
            "version >= 1",
        )


def downgrade() -> None:
    for table_name in reversed(VERSIONED_TABLES):
        op.drop_constraint(f"ck_{table_name}_version_positive", table_name, type_="check")
        op.drop_column(table_name, "version")
