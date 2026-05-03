"""Tests for the public splash endpoint and pre-login privacy policy.

These tests exercise the **security boundary** of US-2.12: the
unauthenticated ``/api/splash`` endpoint must enforce the admin policy
server-side and never leak fields the policy hides.
"""
from __future__ import annotations

import datetime as dt
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calendar import CalendarProvider, Event, SourceCalendar
from app.models.note import Note
from app.models.routine import Routine, TimeBlock
from app.models.user import Household, Profile

pytestmark = pytest.mark.asyncio


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _set_settings(
    db_session: AsyncSession, household: Household, **kwargs: object
) -> None:
    """Merge keys into the household's settings JSON."""
    current = dict(household.settings or {})
    current.update(kwargs)
    household.settings = current
    db_session.add(household)
    await db_session.flush()
    await db_session.refresh(household)


async def _make_event(
    db_session: AsyncSession,
    household: Household,
    profile: Profile,
    *,
    title: str,
    location: str | None,
    start_offset_hours: int,
    duration_hours: int = 1,
) -> Event:
    cal = SourceCalendar(
        household_id=household.id,
        profile_id=profile.id,
        provider=CalendarProvider.local,
        name="Local",
        color="#3b82f6",
    )
    db_session.add(cal)
    await db_session.flush()

    start = datetime.now(timezone.utc) + timedelta(hours=start_offset_hours)
    event = Event(
        source_calendar_id=cal.id,
        profile_id=profile.id,
        title=title,
        location=location,
        start_time=start,
        end_time=start + timedelta(hours=duration_hours),
        all_day=False,
    )
    db_session.add(event)
    await db_session.flush()
    return event


# ── Basic shape & auth ───────────────────────────────────────────────────────


async def test_splash_is_unauthenticated(
    async_client: AsyncClient, sample_household: Household
) -> None:
    # No Authorization header.
    resp = await async_client.get(
        "/api/splash", params={"household_id": str(sample_household.id)}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["household_id"] == str(sample_household.id)
    assert body["household_name"] == sample_household.name
    assert "clock" in body and "policy" in body


async def test_splash_sets_cache_control(
    async_client: AsyncClient, sample_household: Household
) -> None:
    resp = await async_client.get(
        "/api/splash", params={"household_id": str(sample_household.id)}
    )
    assert resp.status_code == 200
    cc = resp.headers.get("Cache-Control", "")
    assert "max-age=30" in cc and "public" in cc


async def test_splash_404_when_no_household_and_none_exist(
    async_client: AsyncClient,
) -> None:
    resp = await async_client.get("/api/splash")
    assert resp.status_code == 404


async def test_splash_auto_picks_single_household(
    async_client: AsyncClient, sample_household: Household
) -> None:
    # No household_id query param — single-household appliance behavior.
    resp = await async_client.get("/api/splash")
    assert resp.status_code == 200
    assert resp.json()["household_id"] == str(sample_household.id)


async def test_splash_400_when_multiple_households_and_no_id(
    async_client: AsyncClient,
    sample_household: Household,
    second_household: Household,
) -> None:
    resp = await async_client.get("/api/splash")
    assert resp.status_code == 400


# ── Calendar mode: off ───────────────────────────────────────────────────────


async def test_calendar_mode_off_includes_full_event_details(
    async_client: AsyncClient,
    db_session: AsyncSession,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    await _make_event(
        db_session, sample_household, sample_profile,
        title="Therapy appointment",
        location="123 Main St",
        start_offset_hours=2,
    )
    await _set_settings(db_session, sample_household, splash_calendar_mode="off")

    resp = await async_client.get(
        "/api/splash", params={"household_id": str(sample_household.id)}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["days"] is not None
    today = body["days"][0]
    assert len(today["events"]) == 1
    ev = today["events"][0]
    assert ev["title"] == "Therapy appointment"
    assert ev["location"] == "123 Main St"
    assert ev["profile_name"] == sample_profile.name


# ── Calendar mode: busy_only (security-critical) ─────────────────────────────


async def test_calendar_mode_busy_only_strips_sensitive_fields(
    async_client: AsyncClient,
    db_session: AsyncSession,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """The serialized response must not contain the original title or
    location anywhere — not just the displayed field. A client cannot
    leak what it never receives."""
    secret_title = "Therapy appointment"
    secret_location = "123 Main St"
    await _make_event(
        db_session, sample_household, sample_profile,
        title=secret_title,
        location=secret_location,
        start_offset_hours=2,
    )
    await _set_settings(db_session, sample_household, splash_calendar_mode="busy_only")

    resp = await async_client.get(
        "/api/splash", params={"household_id": str(sample_household.id)}
    )
    assert resp.status_code == 200

    # Whole-body string check: the secret must never appear, in any field.
    raw = resp.text
    assert secret_title not in raw, "obscured event title leaked into response"
    assert secret_location not in raw, "obscured event location leaked into response"

    body = resp.json()
    today = body["days"][0]
    ev = today["events"][0]
    assert ev["title"] == "Busy"
    assert ev["location"] is None
    # Person color dot must be preserved per US-2.12.3.
    assert ev["profile_color"] == sample_profile.color
    # Profile name should be hidden (it can identify who's busy).
    assert ev["profile_name"] is None


# ── Calendar mode: hidden ────────────────────────────────────────────────────


async def test_calendar_mode_hidden_omits_days_field(
    async_client: AsyncClient,
    db_session: AsyncSession,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    secret_title = "Therapy appointment"
    await _make_event(
        db_session, sample_household, sample_profile,
        title=secret_title, location=None, start_offset_hours=2,
    )
    await _set_settings(db_session, sample_household, splash_calendar_mode="hidden")

    resp = await async_client.get(
        "/api/splash", params={"household_id": str(sample_household.id)}
    )
    assert resp.status_code == 200

    # The agenda block must be entirely absent (None).
    body = resp.json()
    assert body["days"] is None
    # And the secret must not leak via any other field.
    assert secret_title not in resp.text


# ── Per-section toggles ──────────────────────────────────────────────────────


async def test_show_routines_toggle(
    async_client: AsyncClient,
    db_session: AsyncSession,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    routine = Routine(
        household_id=sample_household.id,
        profile_id=sample_profile.id,
        name="Morning Routine",
        time_block=TimeBlock.morning,
        days_of_week=[0, 1, 2, 3, 4, 5, 6],  # every day
        is_active=True,
    )
    db_session.add(routine)
    await db_session.flush()

    # ON
    await _set_settings(db_session, sample_household, splash_show_routines=True)
    resp = await async_client.get(
        "/api/splash", params={"household_id": str(sample_household.id)}
    )
    body = resp.json()
    assert body["routines"] is not None
    assert any(r["name"] == "Morning Routine" for r in body["routines"])
    assert body["policy"]["show_routines"] is True

    # Routine must include assignee + step count + streak (US-2.12.2).
    morning = next(r for r in body["routines"] if r["name"] == "Morning Routine")
    assert morning["assignee"]["name"] == sample_profile.name
    assert morning["assignee"]["color"] == sample_profile.color
    assert "step_count" in morning
    assert "streak_days" in morning
    assert morning["time_block"] == "morning"

    # OFF
    await _set_settings(db_session, sample_household, splash_show_routines=False)
    resp = await async_client.get(
        "/api/splash", params={"household_id": str(sample_household.id)}
    )
    body = resp.json()
    assert body["routines"] is None
    # Routine name must not leak.
    assert "Morning Routine" not in resp.text


async def test_show_messages_toggle_hides_pinned_notes(
    async_client: AsyncClient,
    db_session: AsyncSession,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    note = Note(
        household_id=sample_household.id,
        author_profile_id=sample_profile.id,
        title="Soccer cancelled",
        body="No practice today!",
        pinned=True,
    )
    db_session.add(note)
    await db_session.flush()

    # OFF (default)
    await _set_settings(db_session, sample_household, splash_show_messages=False)
    resp = await async_client.get(
        "/api/splash", params={"household_id": str(sample_household.id)}
    )
    assert resp.json()["messages"] is None
    assert "Soccer cancelled" not in resp.text

    # ON
    await _set_settings(db_session, sample_household, splash_show_messages=True)
    resp = await async_client.get(
        "/api/splash", params={"household_id": str(sample_household.id)}
    )
    body = resp.json()
    assert body["messages"] is not None
    assert any(m["title"] == "Soccer cancelled" for m in body["messages"])


async def test_show_weather_toggle(
    async_client: AsyncClient,
    db_session: AsyncSession,
    sample_household: Household,
) -> None:
    await _set_settings(db_session, sample_household, splash_show_weather=False)
    resp = await async_client.get(
        "/api/splash", params={"household_id": str(sample_household.id)}
    )
    assert resp.json()["weather"] is None

    await _set_settings(
        db_session, sample_household,
        splash_show_weather=True, weather_lat=40.0, weather_lon=-74.0,
    )
    resp = await async_client.get(
        "/api/splash", params={"household_id": str(sample_household.id)}
    )
    body = resp.json()
    assert body["weather"] is not None
    assert body["weather"]["available"] is True


# ── Spill cap ────────────────────────────────────────────────────────────────


async def test_splash_agenda_max_days_cap_is_respected(
    async_client: AsyncClient,
    db_session: AsyncSession,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    # Create one event on each of days 0..6.
    cal = SourceCalendar(
        household_id=sample_household.id,
        profile_id=sample_profile.id,
        provider=CalendarProvider.local,
        name="Local",
    )
    db_session.add(cal)
    await db_session.flush()

    for offset in range(7):
        start = datetime.now(timezone.utc).replace(
            hour=14, minute=0, second=0, microsecond=0
        ) + timedelta(days=offset)
        db_session.add(Event(
            source_calendar_id=cal.id,
            profile_id=sample_profile.id,
            title=f"Day {offset} event",
            start_time=start,
            end_time=start + timedelta(hours=1),
            all_day=False,
        ))
    await db_session.flush()

    await _set_settings(
        db_session, sample_household,
        splash_calendar_mode="off", splash_agenda_max_days=2,
    )
    resp = await async_client.get(
        "/api/splash", params={"household_id": str(sample_household.id)}
    )
    body = resp.json()
    assert len(body["days"]) == 2
    # Day 5+ events must not leak even though they exist in the DB.
    assert "Day 5 event" not in resp.text
    assert "Day 6 event" not in resp.text

    # Bumping the cap brings them back.
    await _set_settings(db_session, sample_household, splash_agenda_max_days=7)
    resp = await async_client.get(
        "/api/splash", params={"household_id": str(sample_household.id)}
    )
    body = resp.json()
    assert len(body["days"]) == 7


# ── Day labels ───────────────────────────────────────────────────────────────


async def test_day_labels(
    async_client: AsyncClient,
    db_session: AsyncSession,
    sample_household: Household,
) -> None:
    await _set_settings(
        db_session, sample_household, splash_agenda_max_days=3,
    )
    resp = await async_client.get(
        "/api/splash", params={"household_id": str(sample_household.id)}
    )
    body = resp.json()
    labels = [d["label"] for d in body["days"]]
    assert labels[0] == "Today"
    assert labels[1] == "Tomorrow"
    # labels[2] is a weekday name; just confirm it isn't one of the
    # special words.
    assert labels[2] not in {"Today", "Tomorrow"}


# ── Policy echo ──────────────────────────────────────────────────────────────


async def test_policy_block_echoes_settings(
    async_client: AsyncClient,
    db_session: AsyncSession,
    sample_household: Household,
) -> None:
    await _set_settings(
        db_session, sample_household,
        splash_mode="alternating",
        splash_alternating_ambient_seconds=45,
        splash_alternating_photo_seconds=90,
        splash_calendar_mode="busy_only",
        splash_agenda_max_days=5,
        splash_show_routines=False,
        splash_show_meals=True,
        splash_show_weather=False,
        splash_show_messages=True,
    )
    resp = await async_client.get(
        "/api/splash", params={"household_id": str(sample_household.id)}
    )
    p = resp.json()["policy"]
    assert p["splash_mode"] == "alternating"
    assert p["splash_alternating_ambient_seconds"] == 45
    assert p["splash_alternating_photo_seconds"] == 90
    assert p["splash_calendar_mode"] == "busy_only"
    assert p["splash_agenda_max_days"] == 5
    assert p["show_routines"] is False
    assert p["show_meals"] is True
    assert p["show_weather"] is False
    assert p["show_messages"] is True
