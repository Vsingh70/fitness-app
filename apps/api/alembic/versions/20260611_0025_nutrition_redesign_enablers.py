"""nutrition redesign enablers: user.nutrition_mode + meal.name

Additive, non-breaking columns for the log-first nutrition redesign:
- ``users.nutrition_mode`` (enum flexible/plan, nullable) — null means the user
  hasn't onboarded yet, so the client shows first-run onboarding.
- ``meals.name`` (varchar(160), nullable) — optional per-meal display name so
  flexible-mode days can render ``Meal {index+1}`` or a user/plan-supplied name
  instead of the legacy meal_type slots.

Revision ID: 0025_nutrition_redesign_enablers
Revises: 0024_perf_indexes
Create Date: 2026-06-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0025_nutrition_redesign_enablers"
down_revision: str | None = "0024_perf_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    nutrition_mode_enum = postgresql.ENUM(
        "flexible",
        "plan",
        name="nutrition_mode",
        create_type=True,
    )
    nutrition_mode_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "users",
        sa.Column(
            "nutrition_mode",
            postgresql.ENUM(name="nutrition_mode", create_type=False),
            nullable=True,
        ),
    )
    op.add_column(
        "meals",
        sa.Column("name", sa.String(160), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("meals", "name")
    op.drop_column("users", "nutrition_mode")
    op.execute("DROP TYPE nutrition_mode")
