"""add block_kind and block_label to program_day_exercises

Slot exercises in a program can now carry a block_kind (warmup/working/cooldown)
and optional block_label, which are copied onto the materialized workout_exercise
when a session is started from the program. This lets warm-up or cooldown
movements declared in a program enter the session as non-working blocks, and
therefore be correctly excluded from working-volume / PR analytics.

The ``block_kind`` Postgres enum type already exists (created with
``workout_exercises``); this migration references it with create_type=False.

Revision ID: 0035_program_day_exercise_block_kind
Revises: 0034_program_goal_endurance
Create Date: 2026-06-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0035_program_day_exercise_block_kind"
down_revision: str | None = "0034_program_goal_endurance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "program_day_exercises",
        sa.Column(
            "block_kind",
            postgresql.ENUM(name="block_kind", create_type=False),
            nullable=False,
            server_default="working",
        ),
    )
    op.add_column(
        "program_day_exercises",
        sa.Column("block_label", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("program_day_exercises", "block_label")
    op.drop_column("program_day_exercises", "block_kind")
