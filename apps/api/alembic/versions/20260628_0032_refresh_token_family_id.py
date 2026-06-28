"""add family_id to refresh_tokens for family-scoped revocation

Refresh-token revocation previously walked the single forward ``rotated_to``
chain, which cannot represent the branch created when the rotation grace path
mints a sibling token. Add a ``family_id`` grouping key so a whole login lineage
(original token + rotations + grace siblings) can be revoked together, and a
replayed/stolen token revokes only its own family rather than every session.

Backfill groups existing rows along ``rotated_to``: each root (a token with no
incoming ``rotated_to``) seeds a family with its own id, propagated forward to
every descendant. Orphans / grace singletons become their own family.

Revision ID: 0032_refresh_token_family_id
Revises: 0031_detach_deleted_identity
Create Date: 2026-06-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0032_refresh_token_family_id"
down_revision: str | None = "0031_detach_deleted_identity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "refresh_tokens",
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    # Group existing rows into families by walking the rotated_to chain forward
    # from each root (a token nothing rotated into).
    op.execute(
        """
        WITH RECURSIVE fam AS (
            SELECT id, id AS family_id
            FROM refresh_tokens rt
            WHERE NOT EXISTS (
                SELECT 1 FROM refresh_tokens p WHERE p.rotated_to = rt.id
            )
            UNION ALL
            SELECT child.id, fam.family_id
            FROM refresh_tokens child
            JOIN refresh_tokens parent ON parent.rotated_to = child.id
            JOIN fam ON fam.id = parent.id
        )
        UPDATE refresh_tokens SET family_id = fam.family_id
        FROM fam WHERE refresh_tokens.id = fam.id
        """
    )
    # Safety net for any row the walk didn't reach (e.g. broken links): be its own family.
    op.execute("UPDATE refresh_tokens SET family_id = id WHERE family_id IS NULL")
    op.alter_column("refresh_tokens", "family_id", nullable=False)
    op.create_index("ix_refresh_tokens_family_id", "refresh_tokens", ["family_id"])


def downgrade() -> None:
    op.drop_index("ix_refresh_tokens_family_id", table_name="refresh_tokens")
    op.drop_column("refresh_tokens", "family_id")
