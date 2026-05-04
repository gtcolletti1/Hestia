"""school day support: routine_steps.school_day_only + school_closures table

Adds a per-step `school_day_only` flag (default False) so steps like
"pack backpack" can be auto-hidden on weekends, US federal holidays, and
admin-marked school closures. The `school_closures` table stores the
admin-marked dates (snow days, in-service days, district holidays).

Revision ID: e8a2c4d6b193
Revises: c7d3e8a91f24
Create Date: 2026-05-04 15:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID


revision: str = "e8a2c4d6b193"
down_revision: Union[str, None] = "c7d3e8a91f24"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "routine_steps",
        sa.Column(
            "school_day_only",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    op.create_table(
        "school_closures",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "household_id",
            UUID(as_uuid=True),
            sa.ForeignKey("households.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column(
            "created_by_profile_id",
            UUID(as_uuid=True),
            sa.ForeignKey("profiles.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "household_id", "date", name="uq_school_closure_household_date"
        ),
    )
    op.create_index(
        "ix_school_closures_household_date",
        "school_closures",
        ["household_id", "date"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_school_closures_household_date", table_name="school_closures"
    )
    op.drop_table("school_closures")
    op.drop_column("routine_steps", "school_day_only")
