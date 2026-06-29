"""add endurance value to the program_goal enum

Adds the ``endurance`` value to the ``program_goal`` enum so cardiovascular
templates/programs (running, cycling, swimming, conditioning) can be filed
under their own goal. The web already exposes an "Endurance" category filter;
this gives it real rows.

Revision ID: 0034_program_goal_endurance
Revises: 0033_foods_fts_index
Create Date: 2026-06-29
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0034_program_goal_endurance"
down_revision: str | None = "0033_foods_fts_index"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ADD VALUE is idempotent with IF NOT EXISTS and, on PG 12+, runs fine under
    # the transaction-per-migration setup as long as the new value isn't read in
    # the same transaction (it isn't — rows using it are seeded post-migrate).
    op.execute("ALTER TYPE program_goal ADD VALUE IF NOT EXISTS 'endurance'")


def downgrade() -> None:
    # Postgres has no DROP VALUE for enum types; the 'endurance' variant stays on
    # program_goal even after downgrade. Acceptable for a single-dev project
    # (mirrors the 0012/0021 enum downgrade notes).
    pass
