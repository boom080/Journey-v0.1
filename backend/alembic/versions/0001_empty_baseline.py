"""Create the empty PostgreSQL baseline for stage 3.

Revision ID: 0001_empty_baseline
Revises:
Create Date: 2026-07-17
"""

from collections.abc import Sequence

revision: str = "0001_empty_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
