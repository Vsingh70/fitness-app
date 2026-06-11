"""programs redesign enablers: program.intensity_mode + exercise.rep_mode

Additive, non-breaking columns for the programs redesign (Direction A):
- ``programs.intensity_mode`` (enum rpe/rir/off, NOT NULL, server_default 'rpe')
  — the program's single global intensity scale. Existing rows stay at 'rpe'
  via the server_default (templates use RPE), so no per-row backfill is needed.
- ``program_day_exercises.rep_mode`` (enum range/target, NOT NULL, server_default
  'range'). Existing rows are backfilled to 'target' when there is no rep span
  (target_reps_high null or equal to target_reps_low), else 'range', so the UI
  renders one number vs a span correctly.

Revision ID: 0026_program_intensity_rep_mode
Revises: 0025_nutrition_redesign_enablers
Create Date: 2026-06-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0026_program_intensity_rep_mode"
down_revision: str | None = "0025_nutrition_redesign_enablers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    intensity_mode_enum = postgresql.ENUM(
        "rpe",
        "rir",
        "off",
        name="intensity_mode",
        create_type=True,
    )
    intensity_mode_enum.create(op.get_bind(), checkfirst=True)

    rep_mode_enum = postgresql.ENUM(
        "range",
        "target",
        name="rep_mode",
        create_type=True,
    )
    rep_mode_enum.create(op.get_bind(), checkfirst=True)

    # Existing programs backfill to 'rpe' via the server_default — templates use
    # RPE, so no per-row program backfill is required.
    op.add_column(
        "programs",
        sa.Column(
            "intensity_mode",
            postgresql.ENUM(name="intensity_mode", create_type=False),
            nullable=False,
            server_default=sa.text("'rpe'::intensity_mode"),
        ),
    )

    op.add_column(
        "program_day_exercises",
        sa.Column(
            "rep_mode",
            postgresql.ENUM(name="rep_mode", create_type=False),
            nullable=False,
            server_default=sa.text("'range'::rep_mode"),
        ),
    )

    # Backfill existing exercises so they render correctly: a single rep goal
    # (no span) is 'target'; a span is 'range'.
    op.execute(
        """
        UPDATE program_day_exercises
        SET rep_mode = CASE
            WHEN target_reps_high IS NULL OR target_reps_high = target_reps_low
                THEN 'target'::rep_mode
            ELSE 'range'::rep_mode
        END
        """
    )


def downgrade() -> None:
    op.drop_column("program_day_exercises", "rep_mode")
    op.drop_column("programs", "intensity_mode")
    op.execute("DROP TYPE rep_mode")
    op.execute("DROP TYPE intensity_mode")
