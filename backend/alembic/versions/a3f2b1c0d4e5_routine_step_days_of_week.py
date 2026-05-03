"""Per-step days_of_week scheduling for routines (Phase B routine UX).

Adds a nullable ``days_of_week`` JSON column to ``routine_steps`` so a
single routine can mix steps that run every day with steps that run only
on specific weekdays (e.g. "Pack backpack" on Mon-Fri only). NULL means
"every day the routine runs" (existing behavior).

Revision ID: a3f2b1c0d4e5
Revises: 9f2a4d8c1e73
Create Date: 2026-05-03 19:40:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a3f2b1c0d4e5"
down_revision: Union[str, None] = "9f2a4d8c1e73"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "routine_steps",
        sa.Column(
            "days_of_week",
            sa.JSON,
            nullable=True,
            comment=(
                "Optional per-step weekday filter (0=Mon..6=Sun). NULL = "
                "applies on every day the parent routine runs."
            ),
        ),
    )


def downgrade() -> None:
    op.drop_column("routine_steps", "days_of_week")
