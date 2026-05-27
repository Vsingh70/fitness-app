"""rpe progression rolling state

Revision ID: 0009_rpe_progression
Revises: 0008_recommendations
Create Date: 2026-05-26
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009_rpe_progression"
down_revision: str | None = "0008_recommendations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "exercise_progression",
        sa.Column(
            "consecutive_above_range",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    op.drop_column("exercise_progression", "consecutive_above_range")
