"""baseline

Revision ID: 0001_baseline
Revises:
Create Date: 2026-05-25
"""

from collections.abc import Sequence

revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Baseline: no app tables yet. Alembic records the version in alembic_version.
    pass


def downgrade() -> None:
    pass
