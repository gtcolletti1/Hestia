"""recurrence overrides

Adds columns needed to model RFC 5545 recurrence exceptions and exdates
correctly so synced events from Google iCal feeds (and other CalDAV
sources) stop flickering on/off when the parser would otherwise collapse
the master series and its modified instances into a single row.

Revision ID: 4a1c9b2d8e10
Revises: ce5ea2e7f589
Create Date: 2026-04-24 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4a1c9b2d8e10"
down_revision: Union[str, None] = "ce5ea2e7f589"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column(
            "master_external_id",
            sa.String(length=512),
            nullable=True,
            comment="Parent UID — same as external_id for masters; UID part for overrides",
        ),
    )
    op.add_column(
        "events",
        sa.Column(
            "recurrence_id",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="UTC instant of overridden master occurrence (override rows only)",
        ),
    )
    op.add_column(
        "events",
        sa.Column(
            "exdates",
            sa.Text(),
            nullable=True,
            comment="Comma-separated UTC ISO datetimes of cancelled master occurrences",
        ),
    )
    op.add_column(
        "events",
        sa.Column(
            "start_tzid",
            sa.String(length=64),
            nullable=True,
            comment="IANA tz of master DTSTART, used for DST-correct RRULE expansion",
        ),
    )
    # Backfill: every existing row is treated as a master with master_external_id = external_id.
    op.execute("UPDATE events SET master_external_id = external_id WHERE master_external_id IS NULL")
    op.create_index(
        "ix_events_master_lookup",
        "events",
        ["source_calendar_id", "master_external_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_events_master_lookup", table_name="events")
    op.drop_column("events", "start_tzid")
    op.drop_column("events", "exdates")
    op.drop_column("events", "recurrence_id")
    op.drop_column("events", "master_external_id")
