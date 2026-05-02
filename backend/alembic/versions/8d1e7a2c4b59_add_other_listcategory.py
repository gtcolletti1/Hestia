"""Add 'other' to listcategory enum and migrate legacy/invalid values.

Adds the new ``other`` enum member, then normalizes any rows that have
``custom`` (deprecated) or the never-valid frontend strings ``shopping``
/ ``chores`` to ``other``. The backend rejects shopping/chores so they
shouldn't exist, but the UPDATE is defensive.

Revision ID: 8d1e7a2c4b59
Revises: 7c4f9b1d3a22
Create Date: 2026-05-02 12:30:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "8d1e7a2c4b59"
down_revision: Union[str, None] = "7c4f9b1d3a22"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # Add the new enum value (PostgreSQL only — SQLite stores enums as TEXT
    # and accepts any string, so this is a no-op there).
    #
    # Note: PostgreSQL 12+ allows ALTER TYPE ... ADD VALUE inside a
    # transaction (the new value just can't be referenced until commit).
    # We deliberately do NOT use op.get_context().autocommit_block() here
    # because it deadlocks when Alembic is invoked in-process from
    # FastAPI startup (see app/database.py:init_db).
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE listcategory ADD VALUE IF NOT EXISTS 'other'")

        # The new enum value isn't usable in this same transaction, so
        # cast through text for the cleanup UPDATE.
        bind.execute(
            sa.text(
                "UPDATE task_lists SET category = 'other'::text::listcategory "
                "WHERE category::text IN ('custom', 'shopping', 'chores')"
            )
        )
    else:
        # SQLite path used in tests.
        bind.execute(
            sa.text(
                "UPDATE task_lists SET category = 'other' "
                "WHERE category IN ('custom', 'shopping', 'chores')"
            )
        )


def downgrade() -> None:
    """Roll any 'other' rows back to 'custom' so the enum value can be
    safely abandoned. We do not drop the enum member itself because
    PostgreSQL does not support removing enum values without recreating
    the type."""
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE task_lists SET category = 'custom' WHERE category = 'other'"
        )
    )
