"""notification_entries inbox table

Persistent log of bell-worthy events (reminder fired, sync error, info).
NULL profile_id = household-wide; otherwise per-profile. read_at NULL = unread.

Revision ID: c4d8e1f72a09
Revises: f1b2d3a4e5c6
Create Date: 2026-05-04 15:50:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID


revision: str = "c4d8e1f72a09"
down_revision: Union[str, None] = "f1b2d3a4e5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notification_entries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "household_id",
            UUID(as_uuid=True),
            sa.ForeignKey("households.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "profile_id",
            UUID(as_uuid=True),
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("kind", sa.String(length=32), nullable=False, server_default="info"),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("link_url", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("read_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_notification_entries_household_id",
        "notification_entries",
        ["household_id"],
    )
    op.create_index(
        "ix_notification_entries_profile_id",
        "notification_entries",
        ["profile_id"],
    )
    op.create_index(
        "ix_notification_entries_created_at",
        "notification_entries",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notification_entries_created_at", table_name="notification_entries"
    )
    op.drop_index(
        "ix_notification_entries_profile_id", table_name="notification_entries"
    )
    op.drop_index(
        "ix_notification_entries_household_id", table_name="notification_entries"
    )
    op.drop_table("notification_entries")
