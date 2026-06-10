"""structured meal plans: kinds, content/tracking modes, day templates, meals, items

Replaces the basic ``meal_plans.days`` jsonb blob with structured tables. Adds
plan kind / content mode / tracking mode enums, program-synced training/rest day
support, manual training-weekday mapping, and weekly-reset review state.

Existing rows are preserved as simple ``targets_only`` ``daily_repeating`` plans:
name + targets + is_active + activated_at are kept; the unstructured ``days``
blob is dropped (it was never finalized) before the column itself is removed.

Revision ID: 0022_structured_meal_plans
Revises: 0021_food_servings_fatsecret
Create Date: 2026-06-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0022_structured_meal_plans"
down_revision: str | None = "0021_food_servings_fatsecret"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PLAN_KINDS = ("daily_repeating", "training_rest", "weekly")
CONTENT_MODES = ("targets_only", "meals_only", "targets_and_meals")
TRACKING_MODES = ("calories_only", "macros_only", "macros_and_calories")
DAY_ROLES = (
    "every_day",
    "training",
    "rest",
    "dow_0",
    "dow_1",
    "dow_2",
    "dow_3",
    "dow_4",
    "dow_5",
    "dow_6",
)
ITEM_UNITS = ("g", "ml", "serving")


def upgrade() -> None:
    plan_kind = postgresql.ENUM(*PLAN_KINDS, name="meal_plan_kind", create_type=True)
    content_mode = postgresql.ENUM(*CONTENT_MODES, name="meal_plan_content_mode", create_type=True)
    tracking_mode = postgresql.ENUM(
        *TRACKING_MODES, name="meal_plan_tracking_mode", create_type=True
    )
    day_role = postgresql.ENUM(*DAY_ROLES, name="meal_plan_day_role", create_type=True)
    item_unit = postgresql.ENUM(*ITEM_UNITS, name="meal_plan_item_unit", create_type=True)
    for enum in (plan_kind, content_mode, tracking_mode, day_role, item_unit):
        enum.create(op.get_bind(), checkfirst=True)

    # --- new meal_plans columns -------------------------------------------
    op.add_column(
        "meal_plans",
        sa.Column(
            "plan_kind",
            postgresql.ENUM(name="meal_plan_kind", create_type=False),
            nullable=False,
            server_default="daily_repeating",
        ),
    )
    op.add_column(
        "meal_plans",
        sa.Column(
            "content_mode",
            postgresql.ENUM(name="meal_plan_content_mode", create_type=False),
            nullable=False,
            server_default="targets_and_meals",
        ),
    )
    op.add_column(
        "meal_plans",
        sa.Column(
            "tracking_mode",
            postgresql.ENUM(name="meal_plan_tracking_mode", create_type=False),
            nullable=False,
            server_default="macros_and_calories",
        ),
    )
    op.add_column(
        "meal_plans",
        sa.Column(
            "synced_to_program",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "meal_plans",
        sa.Column(
            "training_dows",
            postgresql.ARRAY(sa.SmallInteger()),
            nullable=False,
            server_default=sa.text("'{}'::smallint[]"),
        ),
    )
    op.add_column(
        "meal_plans",
        sa.Column(
            "week_resets",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "meal_plans",
        sa.Column(
            "week_start_dow",
            sa.SmallInteger(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "meal_plans",
        sa.Column(
            "needs_week_review",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # Targets become nullable (meals_only plans derive them). Existing rows
    # already have targets and are migrated to content_mode=targets_only below.
    for col in ("target_kcal", "target_protein_g", "target_carbs_g", "target_fat_g"):
        op.alter_column("meal_plans", col, existing_type=sa.Numeric(7, 2), nullable=True)

    # Existing rows: name/targets/is_active/activated_at already preserved by
    # the columns staying in place. Stamp them as simple targets-only daily
    # plans. (server_default already set plan_kind/tracking_mode correctly.)
    op.execute("UPDATE meal_plans SET content_mode = 'targets_only'")

    # Drop the now-superseded unstructured blob.
    op.drop_column("meal_plans", "days")

    # --- meal_plan_days ----------------------------------------------------
    op.create_table(
        "meal_plan_days",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "meal_plan_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("meal_plans.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "day_role",
            postgresql.ENUM(name="meal_plan_day_role", create_type=False),
            nullable=False,
        ),
        sa.Column("target_kcal", sa.Numeric(7, 2), nullable=True),
        sa.Column("target_protein_g", sa.Numeric(7, 2), nullable=True),
        sa.Column("target_carbs_g", sa.Numeric(7, 2), nullable=True),
        sa.Column("target_fat_g", sa.Numeric(7, 2), nullable=True),
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
        sa.UniqueConstraint("meal_plan_id", "day_role", name="uq_meal_plan_days_role"),
    )

    # --- meal_plan_meals ---------------------------------------------------
    op.create_table(
        "meal_plan_meals",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "meal_plan_day_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("meal_plan_days.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("slot_index", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("planned_time", sa.Time(), nullable=True),
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

    # --- meal_plan_items ---------------------------------------------------
    op.create_table(
        "meal_plan_items",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "meal_plan_meal_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("meal_plan_meals.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "food_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("foods.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(10, 3), nullable=False),
        sa.Column(
            "unit",
            postgresql.ENUM(name="meal_plan_item_unit", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "serving_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("food_servings.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("grams", sa.Numeric(10, 2), nullable=False),
        sa.Column("kcal", sa.Numeric(8, 2), nullable=True),
        sa.Column("protein_g", sa.Numeric(7, 2), nullable=True),
        sa.Column("carbs_g", sa.Numeric(7, 2), nullable=True),
        sa.Column("fat_g", sa.Numeric(7, 2), nullable=True),
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


def downgrade() -> None:
    op.drop_table("meal_plan_items")
    op.drop_table("meal_plan_meals")
    op.drop_table("meal_plan_days")

    # Re-add the days blob before dropping the structured columns.
    op.add_column(
        "meal_plans",
        sa.Column(
            "days",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

    # Restore NOT NULL on the core targets (back-fill nulls so the constraint
    # can be re-applied even for rows that were created as meals_only plans).
    for col in ("target_kcal", "target_protein_g", "target_carbs_g", "target_fat_g"):
        op.execute(f"UPDATE meal_plans SET {col} = 0 WHERE {col} IS NULL")
        op.alter_column("meal_plans", col, existing_type=sa.Numeric(7, 2), nullable=False)

    for col in (
        "needs_week_review",
        "week_start_dow",
        "week_resets",
        "training_dows",
        "synced_to_program",
        "tracking_mode",
        "content_mode",
        "plan_kind",
    ):
        op.drop_column("meal_plans", col)

    for name in (
        "meal_plan_item_unit",
        "meal_plan_day_role",
        "meal_plan_tracking_mode",
        "meal_plan_content_mode",
        "meal_plan_kind",
    ):
        sa.Enum(name=name).drop(op.get_bind(), checkfirst=True)
