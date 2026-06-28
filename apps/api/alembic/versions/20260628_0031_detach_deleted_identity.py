"""detach identity from already soft-deleted accounts ("start fresh")

Account deletion now detaches the identity (``email``/``apple_sub``/``google_sub``)
from the soft-deleted row at delete time so the unique keys are freed immediately
and the user can sign in again into a brand-new empty account. This data-only
migration applies the same detachment to accounts that were soft-deleted *before*
that change shipped, so those users are no longer locked out of re-signing-in.

No schema change: the three columns are already nullable with standard
(NULLS-distinct) unique constraints, so multiple soft-deleted rows with NULL
identity coexist fine. The owned data and the ``deleted_at`` stamp are left intact
so the nightly purge still hard-deletes these rows after the grace window.

Revision ID: 0031_detach_deleted_identity
Revises: 0030_user_deleted_at
Create Date: 2026-06-28
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0031_detach_deleted_identity"
down_revision: str | None = "0030_user_deleted_at"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "UPDATE users "
        "SET email = NULL, apple_sub = NULL, google_sub = NULL "
        "WHERE deleted_at IS NOT NULL"
    )


def downgrade() -> None:
    # Irreversible: the detached identities are gone and cannot be restored.
    pass
