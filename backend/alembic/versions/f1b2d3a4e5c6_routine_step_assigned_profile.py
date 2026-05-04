"""routine_steps.assigned_profile_id (per-step chore assignment)

Adds an optional FK from routine_steps to profiles so that an individual
step can be assigned to a specific kid (e.g. "feed the dog" goes to one
profile while "brush teeth" stays unassigned and applies to everyone).

NULL = inherits the routine-level assignment (unchanged behavior).

Revision ID: f1b2d3a4e5c6
Revises: e8a2c4d6b193
Create Date: 2026-05-04 15:30:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID


revision: str = "f1b2d3a4e5c6"
down_revision: Union[str, None] = "e8a2c4d6b193"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "routine_steps",
        sa.Column(
            "assigned_profile_id",
            UUID(as_uuid=True),
            sa.ForeignKey("profiles.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_routine_steps_assigned_profile_id",
        "routine_steps",
        ["assigned_profile_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_routine_steps_assigned_profile_id", table_name="routine_steps")
    op.drop_column("routine_steps", "assigned_profile_id")
