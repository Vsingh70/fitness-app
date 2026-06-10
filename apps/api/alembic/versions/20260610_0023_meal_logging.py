"""meal logging: link logged meals to plan slots + per-item amount/unit/serving

Adds the columns that let a logged ``meal`` trace back to the planned-meal slot
it was materialized from (for plan adherence, delete-forever, and idempotent
re-complete), and extends ``meal_items`` to carry the same amount/unit/serving
shape as ``meal_plan_items`` so flexible tracking can log foods in g / ml / a
named serving while ``grams`` stays the resolved canonical value.

The ``meal_plan_item_unit`` enum (g/ml/serving) introduced in 0022 is reused.

Revision ID: 0023_meal_logging
Revises: 0022_structured_meal_plans
Create Date: 2026-06-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0023_meal_logging"
down_revision: str | None = "0022_structured_meal_plans"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- meals: link to the plan slot it was completed from -----------------
    op.add_column(
        "meals",
        sa.Column(
            "source_plan_meal_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("meal_plan_meals.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "meals",
        sa.Column("source_plan_date", sa.Date(), nullable=True),
    )
    op.create_index(
        "ix_meals_source_plan_slot",
        "meals",
        ["source_plan_meal_id", "source_plan_date"],
    )

    # --- meal_items: amount / unit / serving (grams stays canonical) --------
    op.add_column(
        "meal_items",
        sa.Column("amount", sa.Numeric(10, 3), nullable=True),
    )
    op.add_column(
        "meal_items",
        sa.Column(
            "unit",
            postgresql.ENUM(name="meal_plan_item_unit", create_type=False),
            nullable=False,
            server_default="g",
        ),
    )
    op.add_column(
        "meal_items",
        sa.Column(
            "serving_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("food_servings.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    # Back-fill amount from grams for existing rows (they were unit=g implicitly).
    op.execute("UPDATE meal_items SET amount = grams WHERE amount IS NULL")


def downgrade() -> None:
    op.drop_column("meal_items", "serving_id")
    op.drop_column("meal_items", "unit")
    op.drop_column("meal_items", "amount")

    op.drop_index("ix_meals_source_plan_slot", table_name="meals")
    op.drop_column("meals", "source_plan_date")
    op.drop_column("meals", "source_plan_meal_id")
