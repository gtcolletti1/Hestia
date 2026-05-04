"""Tests for the shared event-expansion helper.

Covers the bug where dashboard / splash agendas double-counted a
recurring master and its overridden instance because they queried the
``events`` table directly with no expansion.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calendar import CalendarProvider, Event, SourceCalendar
from app.services.event_expansion import expand_events_in_range

pytestmark = pytest.mark.asyncio


async def _make_calendar(db_session: AsyncSession, household) -> SourceCalendar:
    cal = SourceCalendar(
        household_id=household.id,
        provider=CalendarProvider.local,
        name="Test Cal",
    )
    db_session.add(cal)
    await db_session.commit()
    await db_session.refresh(cal)
    return cal


async def test_non_recurring_event_passes_through(
    db_session: AsyncSession, sample_household
):
    cal = await _make_calendar(db_session, sample_household)
    start = datetime(2026, 5, 1, 14, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)
    db_session.add(
        Event(
            source_calendar_id=cal.id,
            external_id="evt-1",
            title="One-off",
            start_time=start,
            end_time=end,
        )
    )
    await db_session.commit()

    occs = await expand_events_in_range(
        db_session,
        sample_household.id,
        start - timedelta(hours=2),
        start + timedelta(hours=2),
    )
    assert len(occs) == 1
    assert occs[0].event.title == "One-off"
    assert occs[0].start_time == start


async def test_recurrence_override_dedupes_master_occurrence(
    db_session: AsyncSession, sample_household
):
    """The master + an override at the same slot should yield ONE occurrence."""
    cal = await _make_calendar(db_session, sample_household)

    # Master: weekly Wednesdays at 18:00 UTC starting 2026-05-06
    master_start = datetime(2026, 5, 6, 18, 0, tzinfo=timezone.utc)
    master_end = master_start + timedelta(hours=1)
    db_session.add(
        Event(
            source_calendar_id=cal.id,
            external_id="series-uid",
            master_external_id="series-uid",
            title="Family Game Night",
            location="Living Room",
            start_time=master_start,
            end_time=master_end,
            recurrence_rule="RRULE:FREQ=WEEKLY",
        )
    )

    # Override the 2026-05-13 occurrence with a new location.
    override_start = master_start + timedelta(days=7)
    db_session.add(
        Event(
            source_calendar_id=cal.id,
            external_id="series-uid_20260513T180000Z",
            master_external_id="series-uid",
            recurrence_id=override_start,
            title="Family Game Night",
            location="Backyard",
            start_time=override_start,
            end_time=override_start + timedelta(hours=1),
        )
    )
    await db_session.commit()

    # Query the day of the override.
    day_start = datetime(2026, 5, 13, 0, 0, tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)
    occs = await expand_events_in_range(
        db_session, sample_household.id, day_start, day_end
    )

    # Should be exactly one event (the override), at 18:00 with the new location.
    assert len(occs) == 1, [
        (o.event.title, o.event.location, o.start_time) for o in occs
    ]
    assert occs[0].event.location == "Backyard"
    assert occs[0].start_time == override_start


async def test_recurrence_with_utc_until_and_local_tzid(
    db_session: AsyncSession, sample_household
):
    """Regression: master with TZID + RRULE UNTIL=...Z must expand without
    raising (dateutil rejects naive dtstart paired with aware UNTIL)."""
    cal = await _make_calendar(db_session, sample_household)

    # 11:30 EDT on May 3, 2026 (a Sunday) == 15:30 UTC
    master_start = datetime(2026, 5, 3, 15, 30, tzinfo=timezone.utc)
    master_end = master_start + timedelta(hours=1)
    db_session.add(
        Event(
            source_calendar_id=cal.id,
            external_id="biweekly-uid",
            master_external_id="biweekly-uid",
            title="Bear Den Meeting",
            location="Church",
            start_time=master_start,
            end_time=master_end,
            start_tzid="America/New_York",
            recurrence_rule="FREQ=WEEKLY;UNTIL=20260601T035959Z;INTERVAL=2;BYDAY=SU",
        )
    )

    # Override the May 3 occurrence with a different location.
    db_session.add(
        Event(
            source_calendar_id=cal.id,
            external_id="biweekly-uid#2026-05-03T15:30:00+00:00",
            master_external_id="biweekly-uid",
            recurrence_id=master_start,
            title="Bear Den Meeting",
            location="Police Department",
            start_time=master_start,
            end_time=master_end,
        )
    )
    await db_session.commit()

    day_start = datetime(2026, 5, 3, 0, 0, tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)
    occs = await expand_events_in_range(
        db_session, sample_household.id, day_start, day_end
    )

    assert len(occs) == 1, [
        (o.event.title, o.event.location, o.start_time) for o in occs
    ]
    assert occs[0].event.location == "Police Department"


async def test_exdate_skips_master_occurrence(
    db_session: AsyncSession, sample_household
):
    cal = await _make_calendar(db_session, sample_household)
    master_start = datetime(2026, 5, 6, 18, 0, tzinfo=timezone.utc)
    master_end = master_start + timedelta(hours=1)
    skipped = master_start + timedelta(days=7)
    db_session.add(
        Event(
            source_calendar_id=cal.id,
            external_id="weekly-uid",
            master_external_id="weekly-uid",
            title="Cancelled-week event",
            start_time=master_start,
            end_time=master_end,
            recurrence_rule="RRULE:FREQ=WEEKLY;COUNT=3",
            exdates=skipped.isoformat(),
        )
    )
    await db_session.commit()

    occs = await expand_events_in_range(
        db_session,
        sample_household.id,
        master_start - timedelta(hours=1),
        master_start + timedelta(days=21),
    )
    starts = [o.start_time for o in occs]
    assert master_start in starts
    assert (master_start + timedelta(days=14)) in starts
    assert skipped not in starts
    assert len(occs) == 2
