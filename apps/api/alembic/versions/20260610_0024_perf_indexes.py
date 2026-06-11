"""perf indexes: meals window, meal-item food refs, body metrics, active recs

Composite/partial indexes backing the hot read paths:
- ``meals (user_id, eaten_at) WHERE deleted_at IS NULL`` — the /meals list and
  daily-summary day-window scans.
- ``meal_items (food_id)`` — the food-reference probe on custom-food delete.
- ``body_metrics (user_id, recorded_at DESC)`` — latest-weight lookups + trends.
- ``recommendations (user_id, created_at DESC) WHERE consumed_at IS NULL AND
  dismissed_at IS NULL`` — the active-recommendations list.

Revision ID: 0024_perf_indexes
Revises: 0023_meal_logging
Create Date: 2026-06-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0024_perf_indexes"
down_revision: str | None = "0023_meal_logging"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_meals_user_eaten_not_deleted",
        "meals",
        ["user_id", "eaten_at"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("ix_meal_items_food_id", "meal_items", ["food_id"])
    op.create_index(
        "ix_body_metrics_user_recorded",
        "body_metrics",
        ["user_id", sa.text("recorded_at DESC")],
    )
    op.create_index(
        "ix_recommendations_user_active",
        "recommendations",
        ["user_id", sa.text("created_at DESC")],
        postgresql_where=sa.text("consumed_at IS NULL AND dismissed_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_recommendations_user_active", table_name="recommendations")
    op.drop_index("ix_body_metrics_user_recorded", table_name="body_metrics")
    op.drop_index("ix_meal_items_food_id", table_name="meal_items")
    op.drop_index("ix_meals_user_eaten_not_deleted", table_name="meals")
