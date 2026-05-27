"""extend analytics_insights for the heuristic engine: new enum values,
subject + rationale + surfaced_at columns, partial unique index.

Revision ID: 0012_insights_v2
Revises: 0011_muscle_volume_weekly
Create Date: 2026-05-27
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012_insights_v2"
down_revision: str | None = "0011_muscle_volume_weekly"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


NEW_KINDS = ("weak_muscle", "strong_muscle", "imbalance", "undertrained")


def upgrade() -> None:
    for value in NEW_KINDS:
        op.execute(f"ALTER TYPE analytics_insight_kind ADD VALUE IF NOT EXISTS '{value}'")

    op.add_column(
        "analytics_insights",
        sa.Column("subject", sa.String(120), nullable=True),
    )
    op.add_column(
        "analytics_insights",
        sa.Column("rationale", sa.Text(), nullable=True),
    )
    op.add_column(
        "analytics_insights",
        sa.Column("surfaced_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Partial unique constraint: at most one active insight per (user, kind, subject).
    op.create_index(
        "uq_insights_user_kind_subject_active",
        "analytics_insights",
        ["user_id", "kind", "subject"],
        unique=True,
        postgresql_where=sa.text("dismissed_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_insights_user_kind_subject_active", table_name="analytics_insights")
    op.drop_column("analytics_insights", "surfaced_at")
    op.drop_column("analytics_insights", "rationale")
    op.drop_column("analytics_insights", "subject")
    # NOTE: Postgres has no DROP VALUE for enum types; the new variants stay
    # on the type even after downgrade. Acceptable for a single-dev project.
