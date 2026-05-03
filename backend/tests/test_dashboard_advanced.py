"""Advanced dashboard tests — empty states, time bucketing, widget data.

PRD refs: US-2.1.1 (daily overview), US-2.1.2 (sidebar widgets), Section 8 (edge cases).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calendar import Event, SourceCalendar
from app.models.calendar import CalendarProvider
from app.models.routine import Routine, RoutineStep, TimeBlock
from app.models.user import Household, Profile
from app.services.routine_window import current_time_block

pytestmark = pytest.mark.asyncio


# ── Tests ────────────────────────────────────────────────────────────────────


async def test_dashboard_empty_agenda(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    """With no events, agenda buckets exist but each has empty events list."""
    resp = await authed_client.get(
        "/api/dashboard",
        params={"household_id": str(sample_household.id)},
    )
    assert resp.status_code == 200
    for bucket in resp.json()["agenda"]:
        assert isinstance(bucket["events"], list)
        assert len(bucket["events"]) == 0


async def test_dashboard_empty_routines(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    """With no routines, active_routines is an empty list."""
    resp = await authed_client.get(
        "/api/dashboard",
        params={"household_id": str(sample_household.id)},
    )
    assert resp.status_code == 200
    assert resp.json()["active_routines"] == []


async def test_dashboard_empty_meals(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    """With no meals planned, today_meals is an empty list."""
    resp = await authed_client.get(
        "/api/dashboard",
        params={"household_id": str(sample_household.id)},
    )
    assert resp.status_code == 200
    assert resp.json()["today_meals"] == []


async def test_dashboard_empty_lists(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    """With no lists, active_lists is an empty list."""
    resp = await authed_client.get(
        "/api/dashboard",
        params={"household_id": str(sample_household.id)},
    )
    assert resp.status_code == 200
    assert resp.json()["active_lists"] == []


async def test_dashboard_event_morning_bucket(
    authed_client: AsyncClient,
    sample_household: Household,
    db_session: AsyncSession,
) -> None:
    """A 9AM event lands in the 'morning' bucket."""
    cal = SourceCalendar(
        household_id=sample_household.id,
        provider=CalendarProvider.local,
        name="Test Cal",
    )
    db_session.add(cal)
    await db_session.flush()

    today = date.today()
    event = Event(
        source_calendar_id=cal.id,
        title="Morning Meeting",
        start_time=datetime.combine(today, time(9, 0)),
        end_time=datetime.combine(today, time(10, 0)),
    )
    db_session.add(event)
    await db_session.flush()

    resp = await authed_client.get(
        "/api/dashboard",
        params={"household_id": str(sample_household.id)},
    )
    morning = resp.json()["agenda"][0]
    assert morning["bucket"] == "morning"
    assert any(e["title"] == "Morning Meeting" for e in morning["events"])


async def test_dashboard_event_afternoon_bucket(
    authed_client: AsyncClient,
    sample_household: Household,
    db_session: AsyncSession,
) -> None:
    """A 2PM event lands in the 'afternoon' bucket."""
    cal = SourceCalendar(
        household_id=sample_household.id,
        provider=CalendarProvider.local,
        name="Test Cal 2",
    )
    db_session.add(cal)
    await db_session.flush()

    today = date.today()
    event = Event(
        source_calendar_id=cal.id,
        title="Afternoon Walk",
        start_time=datetime.combine(today, time(14, 0)),
        end_time=datetime.combine(today, time(15, 0)),
    )
    db_session.add(event)
    await db_session.flush()

    resp = await authed_client.get(
        "/api/dashboard",
        params={"household_id": str(sample_household.id)},
    )
    afternoon = resp.json()["agenda"][1]
    assert afternoon["bucket"] == "afternoon"
    assert any(e["title"] == "Afternoon Walk" for e in afternoon["events"])


async def test_dashboard_event_evening_bucket(
    authed_client: AsyncClient,
    sample_household: Household,
    db_session: AsyncSession,
) -> None:
    """A 7PM event lands in the 'evening' bucket."""
    cal = SourceCalendar(
        household_id=sample_household.id,
        provider=CalendarProvider.local,
        name="Test Cal 3",
    )
    db_session.add(cal)
    await db_session.flush()

    today = date.today()
    event = Event(
        source_calendar_id=cal.id,
        title="Dinner Party",
        start_time=datetime.combine(today, time(19, 0)),
        end_time=datetime.combine(today, time(21, 0)),
    )
    db_session.add(event)
    await db_session.flush()

    resp = await authed_client.get(
        "/api/dashboard",
        params={"household_id": str(sample_household.id)},
    )
    evening = resp.json()["agenda"][2]
    assert evening["bucket"] == "evening"
    assert any(e["title"] == "Dinner Party" for e in evening["events"])


async def test_dashboard_routines_only_today(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """Dashboard only shows routines whose days_of_week includes today."""
    today_weekday = date.today().weekday()  # 0=Mon
    other_day = (today_weekday + 1) % 7
    block_now = current_time_block(datetime.now().time()).value

    # Routine for today
    await authed_client.post(
        "/api/routines",
        json={
            "household_id": str(sample_household.id),
            "name": "Today Only",
            "time_block": block_now,
            "days_of_week": [today_weekday],
            "steps": [{"label": "Do it", "sort_order": 0}],
        },
    )

    # Routine for a different day
    await authed_client.post(
        "/api/routines",
        json={
            "household_id": str(sample_household.id),
            "name": "Other Day Only",
            "time_block": block_now,
            "days_of_week": [other_day],
            "steps": [{"label": "Skip it", "sort_order": 0}],
        },
    )

    resp = await authed_client.get(
        "/api/dashboard",
        params={"household_id": str(sample_household.id)},
    )
    routines = resp.json()["active_routines"]
    names = [r["name"] for r in routines]
    assert "Today Only" in names
    assert "Other Day Only" not in names


async def test_dashboard_routine_has_step_count(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """Dashboard routine objects include step_count."""
    today_weekday = date.today().weekday()
    block_now = current_time_block(datetime.now().time()).value

    await authed_client.post(
        "/api/routines",
        json={
            "household_id": str(sample_household.id),
            "name": "Count Test",
            "time_block": block_now,
            "days_of_week": [today_weekday],
            "steps": [
                {"label": "A", "sort_order": 0},
                {"label": "B", "sort_order": 1},
            ],
        },
    )

    resp = await authed_client.get(
        "/api/dashboard",
        params={"household_id": str(sample_household.id)},
    )
    routine = next(
        r for r in resp.json()["active_routines"] if r["name"] == "Count Test"
    )
    assert routine["step_count"] == 2


async def test_dashboard_cross_household_denied(
    authed_client: AsyncClient, second_household: Household
) -> None:
    """Cannot fetch another household's dashboard."""
    resp = await authed_client.get(
        "/api/dashboard",
        params={"household_id": str(second_household.id)},
    )
    assert resp.status_code == 403


async def test_dashboard_tz_excludes_yesterday_evening_event(
    authed_client: AsyncClient,
    sample_household: Household,
    db_session: AsyncSession,
) -> None:
    """Regression: a 7pm-EDT event on the user's *yesterday* must not appear
    on today's agenda just because it overlaps today in UTC.

    Pre-fix behavior: server used `date.today()` (UTC) so an event at
    23:00Z on 04-27 (= 19:00 EDT 04-27) was filtered as "today" when UTC
    rolled past midnight, even though America/New_York was still 04-27.
    """
    cal = SourceCalendar(
        household_id=sample_household.id,
        provider=CalendarProvider.local,
        name="Test Cal",
    )
    db_session.add(cal)
    await db_session.flush()

    # Pin a known UTC instant: today 04:00 UTC = yesterday 00:00 EDT.
    # Use the local-tz today as the reference, then put the event squarely
    # in *yesterday local* but *today UTC* (i.e. between 04:00 and 04:59 UTC
    # only works if local-now is past midnight UTC). Simpler: put event
    # 23:00-23:30 UTC of UTC's "today" — that's evening EDT yesterday or
    # afternoon Pacific yesterday. Use Pacific to dodge edge cases.
    utc_today = datetime.now(timezone.utc).date()
    # Event at 04:00-04:30 UTC = 21:00-21:30 PDT *yesterday* (UTC-7).
    event = Event(
        source_calendar_id=cal.id,
        title="Yesterday Evening (PDT)",
        start_time=datetime.combine(utc_today, time(4, 0), tzinfo=timezone.utc),
        end_time=datetime.combine(utc_today, time(4, 30), tzinfo=timezone.utc),
    )
    db_session.add(event)
    await db_session.flush()

    # No tz: defaults to UTC, event falls inside UTC-today window.
    resp_utc = await authed_client.get(
        "/api/dashboard",
        params={"household_id": str(sample_household.id)},
    )
    titles_utc = [
        e["title"] for b in resp_utc.json()["agenda"] for e in b["events"]
    ]
    assert "Yesterday Evening (PDT)" in titles_utc

    # With Pacific tz, the same event is yesterday-local and must be excluded.
    resp_pdt = await authed_client.get(
        "/api/dashboard",
        params={
            "household_id": str(sample_household.id),
            "tz": "America/Los_Angeles",
        },
    )
    titles_pdt = [
        e["title"] for b in resp_pdt.json()["agenda"] for e in b["events"]
    ]
    assert "Yesterday Evening (PDT)" not in titles_pdt


async def test_dashboard_tz_buckets_by_local_time(
    authed_client: AsyncClient,
    sample_household: Household,
    db_session: AsyncSession,
) -> None:
    """An event at 14:00Z is afternoon in EDT (10am) → morning, not afternoon."""
    cal = SourceCalendar(
        household_id=sample_household.id,
        provider=CalendarProvider.local,
        name="Test Cal",
    )
    db_session.add(cal)
    await db_session.flush()

    # 14:00 UTC = 10:00 EDT (UTC-4) = morning.
    today_eastern = datetime.now(ZoneInfo("America/New_York")).date()
    start_local = datetime.combine(today_eastern, time(10, 0), tzinfo=ZoneInfo("America/New_York"))
    event = Event(
        source_calendar_id=cal.id,
        title="10am Eastern",
        start_time=start_local.astimezone(timezone.utc),
        end_time=(start_local + timedelta(hours=1)).astimezone(timezone.utc),
    )
    db_session.add(event)
    await db_session.flush()

    resp = await authed_client.get(
        "/api/dashboard",
        params={
            "household_id": str(sample_household.id),
            "tz": "America/New_York",
        },
    )
    body = resp.json()
    morning = next(b for b in body["agenda"] if b["bucket"] == "morning")
    afternoon = next(b for b in body["agenda"] if b["bucket"] == "afternoon")
    assert any(e["title"] == "10am Eastern" for e in morning["events"])
    assert not any(e["title"] == "10am Eastern" for e in afternoon["events"])


async def test_dashboard_invalid_tz_falls_back_to_utc(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    """A bogus tz string must not 500 — endpoint silently uses UTC."""
    resp = await authed_client.get(
        "/api/dashboard",
        params={
            "household_id": str(sample_household.id),
            "tz": "Not/A_Real_Zone",
        },
    )
    assert resp.status_code == 200
