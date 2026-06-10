"""fatsecret food source enum value + food_servings table

Adds the ``fatsecret`` value to the ``food_source`` enum and a ``food_servings``
table holding named servings (e.g. "1 cup", "100 g") with a resolved gram
weight. The per-100g macro columns on ``foods`` stay the canonical math base.

Revision ID: 0021_food_servings_fatsecret
Revises: 0020_periodization_mode
Create Date: 2026-06-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0021_food_servings_fatsecret"
down_revision: str | None = "0020_periodization_mode"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Extend the existing food_source enum. ADD VALUE is idempotent and, on
    # PG 12+, runs fine under the transaction-per-migration setup as long as the
    # value isn't read in the same transaction (it isn't here).
    op.execute("ALTER TYPE food_source ADD VALUE IF NOT EXISTS 'fatsecret'")

    serving_unit = postgresql.ENUM("g", "ml", name="serving_unit", create_type=True)
    serving_unit.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "food_servings",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "food_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("foods.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("description", sa.String(240), nullable=False),
        sa.Column("metric_amount", sa.Numeric(10, 3), nullable=True),
        sa.Column(
            "metric_unit",
            postgresql.ENUM(name="serving_unit", create_type=False),
            nullable=True,
        ),
        sa.Column("grams", sa.Numeric(10, 3), nullable=True),
        sa.Column(
            "is_default",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_food_servings_food_id", "food_servings", ["food_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_food_servings_food_id", table_name="food_servings")
    op.drop_table("food_servings")
    op.execute("DROP TYPE serving_unit")
    # NOTE: Postgres has no DROP VALUE for enum types; the 'fatsecret' variant
    # stays on food_source even after downgrade. Acceptable for a single-dev
    # project (mirrors the 0012 insights enum downgrade note).
