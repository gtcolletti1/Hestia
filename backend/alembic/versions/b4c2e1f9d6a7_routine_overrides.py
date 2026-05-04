"""Routine overrides (Phase C parental override).

Adds a ``routine_overrides`` table for per-routine pause / skip-today and
household-wide vacation pauses, plus a ``pausable_on_vacation`` flag on
``routines`` so admins can opt out specific routines from household-wide
pauses (e.g. medications still run during vacation).

Revision ID: b4c2e1f9d6a7
Revises: a3f2b1c0d4e5
Create Date: 2026-05-03 20:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID


revision: str = "b4c2e1f9d6a7"
down_revision: Union[str, None] = "a3f2b1c0d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "routines",
        sa.Column(
            "pausable_on_vacation",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )

    op.create_table(
        "routine_overrides",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "household_id",
            UUID(as_uuid=True),
            sa.ForeignKey("households.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "routine_id",
            UUID(as_uuid=True),
            sa.ForeignKey("routines.id", ondelete="CASCADE"),
            nullable=True,
            comment="NULL = household-wide override (vacation mode).",
        ),
        sa.Column(
            "kind",
            sa.String(16),
            nullable=False,
            comment="'pause' or 'skip'.",
        ),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column(
            "end_date",
            sa.Date(),
            nullable=True,
            comment="NULL for an indefinite pause; equals start_date for a single-day skip.",
        ),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column(
            "created_by_profile_id",
            UUID(as_uuid=True),
            sa.ForeignKey("profiles.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "kind in ('pause', 'skip')", name="ck_routine_override_kind"
        ),
    )
    op.create_index(
        "ix_routine_overrides_household",
        "routine_overrides",
        ["household_id", "start_date", "end_date"],
    )
    op.create_index(
        "ix_routine_overrides_routine",
        "routine_overrides",
        ["routine_id", "start_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_routine_overrides_routine", table_name="routine_overrides")
    op.drop_index("ix_routine_overrides_household", table_name="routine_overrides")
    op.drop_table("routine_overrides")
    op.drop_column("routines", "pausable_on_vacation")
