"""meals, meal_items, meal_plans, body_metrics; height_cm on users

Revision ID: 0014_meals
Revises: 0013_foods
Create Date: 2026-05-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0014_meals"
down_revision: str | None = "0013_foods"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


MEAL_TYPES = ("breakfast", "lunch", "dinner", "snack")


def upgrade() -> None:
    op.add_column("users", sa.Column("height_cm", sa.Numeric(5, 2), nullable=True))

    meal_type = postgresql.ENUM(*MEAL_TYPES, name="meal_type", create_type=True)
    meal_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "meals",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("eaten_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column(
            "meal_type",
            postgresql.ENUM(name="meal_type", create_type=False),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("photo_url", sa.Text(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "meal_items",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "meal_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("meals.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "food_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("foods.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("grams", sa.Numeric(8, 2), nullable=False),
        sa.Column("kcal", sa.Numeric(8, 2), nullable=True),
        sa.Column("protein_g", sa.Numeric(7, 2), nullable=True),
        sa.Column("carbs_g", sa.Numeric(7, 2), nullable=True),
        sa.Column("fat_g", sa.Numeric(7, 2), nullable=True),
        sa.Column("fiber_g", sa.Numeric(7, 2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "meal_plans",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("target_kcal", sa.Numeric(7, 2), nullable=False),
        sa.Column("target_protein_g", sa.Numeric(7, 2), nullable=False),
        sa.Column("target_carbs_g", sa.Numeric(7, 2), nullable=False),
        sa.Column("target_fat_g", sa.Numeric(7, 2), nullable=False),
        sa.Column("target_fiber_g", sa.Numeric(7, 2), nullable=True),
        sa.Column(
            "days",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "uq_meal_plans_active_per_user",
        "meal_plans",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_active AND deleted_at IS NULL"),
    )

    op.create_table(
        "body_metrics",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("weight_kg", sa.Numeric(6, 2), nullable=True),
        sa.Column("body_fat_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("body_metrics")
    op.drop_index("uq_meal_plans_active_per_user", table_name="meal_plans")
    op.drop_table("meal_plans")
    op.drop_table("meal_items")
    op.drop_table("meals")
    sa.Enum(name="meal_type").drop(op.get_bind(), checkfirst=True)
    op.drop_column("users", "height_cm")
