"""mesocycles, deloads, fatigue, insights

Revision ID: 0010_mesocycles
Revises: 0009_rpe_progression
Create Date: 2026-05-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0010_mesocycles"
down_revision: str | None = "0009_rpe_progression"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Programs gain meso-length + auto-deload flags.
    op.add_column(
        "programs",
        sa.Column(
            "mesocycle_length_weeks",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("4"),
        ),
    )
    op.add_column(
        "programs",
        sa.Column(
            "auto_deload",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )

    # Per-user rolling fatigue accumulator.
    op.create_table(
        "user_fatigue_state",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "rolling_7d_score",
            sa.Numeric(6, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("last_event_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_insight_at", sa.DateTime(timezone=True), nullable=True),
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

    kind_enum = postgresql.ENUM(
        "stagnation",
        "volume_drop",
        "frequency_drop",
        "pr_streak",
        name="analytics_insight_kind",
        create_type=True,
    )
    kind_enum.create(op.get_bind(), checkfirst=True)
    severity_enum = postgresql.ENUM(
        "info",
        "warn",
        "action",
        name="analytics_insight_severity",
        create_type=True,
    )
    severity_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "analytics_insights",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "kind",
            postgresql.ENUM(name="analytics_insight_kind", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "severity",
            postgresql.ENUM(name="analytics_insight_severity", create_type=False),
            nullable=False,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
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
        "ix_analytics_insights_user_active",
        "analytics_insights",
        ["user_id", "created_at"],
        unique=False,
        postgresql_where=sa.text("dismissed_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_analytics_insights_user_active", table_name="analytics_insights")
    op.drop_table("analytics_insights")
    op.execute("DROP TYPE analytics_insight_severity")
    op.execute("DROP TYPE analytics_insight_kind")

    op.drop_table("user_fatigue_state")

    op.drop_column("programs", "auto_deload")
    op.drop_column("programs", "mesocycle_length_weeks")
