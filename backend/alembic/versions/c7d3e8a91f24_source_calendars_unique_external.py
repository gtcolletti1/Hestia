"""source_calendars unique external_id

Adds a partial unique index so the same external calendar (Google,
Outlook, CalDAV, iCal) can't be connected twice within one household —
the silent root cause of duplicated agenda entries when a user
re-connected a calendar without removing the old SourceCalendar row.

Local calendars and rows with no external_id are excluded so users can
freely create multiple manual calendars.

Revision ID: c7d3e8a91f24
Revises: b4c2e1f9d6a7
Create Date: 2026-05-04 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "c7d3e8a91f24"
down_revision: Union[str, None] = "b4c2e1f9d6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INDEX_NAME = "uq_source_calendars_household_provider_external"


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    # Defensive: collapse pre-existing duplicates so the unique index can
    # be created. Strategy: pick the oldest row per (household, provider,
    # external_id) as the "keeper", repoint events off the duplicates,
    # then delete the duplicates. UUID columns can't be MIN()'d in
    # Postgres so we go through ROW_NUMBER().
    if dialect == "postgresql":
        op.execute(
            """
            WITH ranked AS (
                SELECT id, household_id, provider, external_id,
                       ROW_NUMBER() OVER (
                           PARTITION BY household_id, provider, external_id
                           ORDER BY created_at, id
                       ) AS rn,
                       FIRST_VALUE(id) OVER (
                           PARTITION BY household_id, provider, external_id
                           ORDER BY created_at, id
                       ) AS keeper_id
                FROM source_calendars
                WHERE provider <> 'local' AND external_id IS NOT NULL
            ),
            moves AS (SELECT id, keeper_id FROM ranked WHERE rn > 1)
            UPDATE events SET source_calendar_id = m.keeper_id
            FROM moves m WHERE events.source_calendar_id = m.id;
            """
        )
        op.execute(
            """
            WITH ranked AS (
                SELECT id, ROW_NUMBER() OVER (
                    PARTITION BY household_id, provider, external_id
                    ORDER BY created_at, id
                ) AS rn
                FROM source_calendars
                WHERE provider <> 'local' AND external_id IS NOT NULL
            )
            DELETE FROM source_calendars
            WHERE id IN (SELECT id FROM ranked WHERE rn > 1);
            """
        )
    else:
        # SQLite path used only by the test suite — no production data.
        op.execute(
            """
            UPDATE events SET source_calendar_id = (
                SELECT s2.id FROM source_calendars s1
                JOIN source_calendars s2 USING (household_id, provider, external_id)
                WHERE s1.id = events.source_calendar_id
                  AND s1.provider <> 'local'
                  AND s1.external_id IS NOT NULL
                ORDER BY s2.created_at, s2.id
                LIMIT 1
            )
            WHERE EXISTS (
                SELECT 1 FROM source_calendars s1
                WHERE s1.id = events.source_calendar_id
                  AND s1.provider <> 'local'
                  AND s1.external_id IS NOT NULL
            );
            """
        )
        op.execute(
            """
            DELETE FROM source_calendars
            WHERE id IN (
                SELECT s.id FROM source_calendars s
                WHERE s.provider <> 'local' AND s.external_id IS NOT NULL
                  AND s.id NOT IN (
                    SELECT (
                        SELECT s2.id FROM source_calendars s2
                        WHERE s2.household_id = s.household_id
                          AND s2.provider = s.provider
                          AND s2.external_id = s.external_id
                        ORDER BY s2.created_at, s2.id LIMIT 1
                    )
                    FROM source_calendars s3
                    WHERE s3.id = s.id
                  )
            );
            """
        )

    if dialect == "postgresql":
        op.create_index(
            INDEX_NAME,
            "source_calendars",
            ["household_id", "provider", "external_id"],
            unique=True,
            postgresql_where="provider != 'local' AND external_id IS NOT NULL",
        )
    else:
        op.execute(
            "CREATE UNIQUE INDEX "
            + INDEX_NAME
            + " ON source_calendars (household_id, provider, external_id) "
            + "WHERE provider != 'local' AND external_id IS NOT NULL"
        )


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="source_calendars")
