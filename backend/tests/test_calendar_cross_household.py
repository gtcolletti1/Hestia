"""Cross-household access tests for calendar endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calendar import CalendarProvider, SourceCalendar
from app.models.user import Household, Profile

pytestmark = pytest.mark.asyncio


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _create_calendar_and_event(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
) -> tuple[str, str]:
    """Create a source calendar and event in the given household. Returns (calendar_id, event_id)."""
    cal = SourceCalendar(
        household_id=household.id,
        name="Family Calendar",
        provider=CalendarProvider.local,
    )
    db_session.add(cal)
    await db_session.flush()
    await db_session.refresh(cal)

    now = datetime.now(timezone.utc)
    resp = await client.post(
        "/api/events",
        json={
            "source_calendar_id": str(cal.id),
            "title": "Family Dinner",
            "start_time": now.isoformat(),
            "end_time": (now + timedelta(hours=1)).isoformat(),
        },
    )
    assert resp.status_code == 201
    return str(cal.id), resp.json()["id"]


# ── Cross-household event tests ──────────────────────────────────────────────


async def test_cross_household_list_events(
    authed_client: AsyncClient,
    second_authed_client: AsyncClient,
    sample_household: Household,
    db_session: AsyncSession,
) -> None:
    """User from household B cannot list events for household A."""
    await _create_calendar_and_event(authed_client, db_session, sample_household)
    today = datetime.now(timezone.utc).date()

    resp = await second_authed_client.get(
        "/api/events",
        params={
            "household_id": str(sample_household.id),
            "start_date": str(today),
            "end_date": str(today + timedelta(days=7)),
        },
    )
    assert resp.status_code == 403


async def test_cross_household_get_event(
    authed_client: AsyncClient,
    second_authed_client: AsyncClient,
    sample_household: Household,
    db_session: AsyncSession,
) -> None:
    """User from household B cannot get a specific event from household A."""
    _cal_id, event_id = await _create_calendar_and_event(authed_client, db_session, sample_household)

    resp = await second_authed_client.get(f"/api/events/{event_id}")
    assert resp.status_code == 403


async def test_cross_household_create_event(
    authed_client: AsyncClient,
    second_authed_client: AsyncClient,
    sample_household: Household,
    db_session: AsyncSession,
) -> None:
    """User from household B cannot create an event on household A's calendar."""
    cal_id, _ = await _create_calendar_and_event(authed_client, db_session, sample_household)
    now = datetime.now(timezone.utc)

    resp = await second_authed_client.post(
        "/api/events",
        json={
            "source_calendar_id": cal_id,
            "title": "Hacked Event",
            "start_time": now.isoformat(),
            "end_time": (now + timedelta(hours=1)).isoformat(),
        },
    )
    assert resp.status_code == 403


async def test_cross_household_update_event(
    authed_client: AsyncClient,
    second_authed_client: AsyncClient,
    sample_household: Household,
    db_session: AsyncSession,
) -> None:
    """User from household B cannot update household A's event."""
    _cal_id, event_id = await _create_calendar_and_event(authed_client, db_session, sample_household)

    resp = await second_authed_client.put(
        f"/api/events/{event_id}",
        json={"title": "Tampered Event"},
    )
    assert resp.status_code == 403


async def test_cross_household_delete_event(
    authed_client: AsyncClient,
    second_authed_client: AsyncClient,
    sample_household: Household,
    db_session: AsyncSession,
) -> None:
    """User from household B cannot delete household A's event."""
    _cal_id, event_id = await _create_calendar_and_event(authed_client, db_session, sample_household)

    resp = await second_authed_client.delete(f"/api/events/{event_id}")
    assert resp.status_code == 403


# ── Cross-household source calendar tests ────────────────────────────────────


async def test_cross_household_list_calendars(
    authed_client: AsyncClient,
    second_authed_client: AsyncClient,
    sample_household: Household,
    db_session: AsyncSession,
) -> None:
    """User from household B cannot list household A's calendars."""
    resp = await second_authed_client.get(
        "/api/calendars",
        params={"household_id": str(sample_household.id)},
    )
    assert resp.status_code == 403


async def test_cross_household_create_calendar(
    second_authed_client: AsyncClient,
    sample_household: Household,
) -> None:
    """User from household B cannot create a calendar in household A."""
    resp = await second_authed_client.post(
        "/api/calendars",
        json={
            "household_id": str(sample_household.id),
            "name": "Hacked Calendar",
            "provider": "local",
        },
    )
    assert resp.status_code == 403


async def test_cross_household_update_calendar(
    authed_client: AsyncClient,
    second_authed_client: AsyncClient,
    sample_household: Household,
    db_session: AsyncSession,
) -> None:
    """User from household B cannot update household A's calendar."""
    cal_id, _ = await _create_calendar_and_event(authed_client, db_session, sample_household)

    resp = await second_authed_client.put(
        f"/api/calendars/{cal_id}",
        json={"name": "Tampered Calendar"},
    )
    assert resp.status_code == 403


async def test_cross_household_delete_calendar(
    authed_client: AsyncClient,
    second_authed_client: AsyncClient,
    sample_household: Household,
    db_session: AsyncSession,
) -> None:
    """User from household B cannot delete household A's calendar."""
    cal_id, _ = await _create_calendar_and_event(authed_client, db_session, sample_household)

    resp = await second_authed_client.delete(f"/api/calendars/{cal_id}")
    assert resp.status_code == 403
