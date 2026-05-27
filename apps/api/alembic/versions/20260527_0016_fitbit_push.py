"""workout_sessions.fitbit_log_id + fitbit_pushed_at; users.auto_push_to_fitbit

Revision ID: 0016_fitbit_push
Revises: 0015_fitbit
Create Date: 2026-05-27
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0016_fitbit_push"
down_revision: str | None = "0015_fitbit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "workout_sessions",
        sa.Column("fitbit_log_id", sa.String(64), nullable=True),
    )
    op.add_column(
        "workout_sessions",
        sa.Column("fitbit_pushed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "auto_push_to_fitbit",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "auto_push_to_fitbit")
    op.drop_column("workout_sessions", "fitbit_pushed_at")
    op.drop_column("workout_sessions", "fitbit_log_id")
