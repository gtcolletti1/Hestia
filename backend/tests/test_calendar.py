"""Tests for the calendar & events API."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calendar import CalendarProvider, SourceCalendar
from app.models.user import Household, Profile

pytestmark = pytest.mark.asyncio


# ── Helpers / fixtures ───────────────────────────────────────────────────────


@pytest_asyncio.fixture()
async def source_calendar(
    db_session: AsyncSession, sample_household: Household
) -> SourceCalendar:
    cal = SourceCalendar(
        household_id=sample_household.id,
        name="Family Calendar",
        provider=CalendarProvider.local,
    )
    db_session.add(cal)
    await db_session.flush()
    await db_session.refresh(cal)
    return cal


def _event_payload(
    source_calendar_id: uuid.UUID,
    title: str = "Team Meeting",
    start_offset_days: int = 0,
) -> dict:
    now = datetime.now(timezone.utc) + timedelta(days=start_offset_days)
    return {
        "source_calendar_id": str(source_calendar_id),
        "title": title,
        "start_time": (now).isoformat(),
        "end_time": (now + timedelta(hours=1)).isoformat(),
    }


# ── Source Calendar ──────────────────────────────────────────────────────────


async def test_create_source_calendar(
    async_client: AsyncClient, sample_household: Household
) -> None:
    resp = await async_client.post(
        "/api/calendars",
        json={
            "household_id": str(sample_household.id),
            "name": "Work Calendar",
            "provider": "local",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Work Calendar"
    assert body["provider"] == "local"
    assert body["household_id"] == str(sample_household.id)


# ── Events CRUD ──────────────────────────────────────────────────────────────


async def test_create_event(
    async_client: AsyncClient, source_calendar: SourceCalendar
) -> None:
    payload = _event_payload(source_calendar.id)
    resp = await async_client.post("/api/events", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Team Meeting"
    assert "id" in body


async def test_list_events_by_date_range(
    async_client: AsyncClient,
    sample_household: Household,
    source_calendar: SourceCalendar,
) -> None:
    today = datetime.now(timezone.utc).date()

    # Create events at different dates
    for offset in (0, 2, 5):
        await async_client.post(
            "/api/events",
            json=_event_payload(source_calendar.id, f"Evt-{offset}", offset),
        )

    # Query a narrow range that should include only today and +2
    resp = await async_client.get(
        "/api/events",
        params={
            "household_id": str(sample_household.id),
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=3)).isoformat(),
        },
    )
    assert resp.status_code == 200
    events = resp.json()
    assert isinstance(events, list)
    titles = [e["title"] for e in events]
    assert "Evt-0" in titles
    assert "Evt-2" in titles
    assert "Evt-5" not in titles


async def test_update_event(
    async_client: AsyncClient, source_calendar: SourceCalendar
) -> None:
    create = await async_client.post(
        "/api/events", json=_event_payload(source_calendar.id)
    )
    event_id = create.json()["id"]

    resp = await async_client.put(
        f"/api/events/{event_id}", json={"title": "Renamed Event"}
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Renamed Event"


async def test_delete_event(
    async_client: AsyncClient, source_calendar: SourceCalendar
) -> None:
    create = await async_client.post(
        "/api/events", json=_event_payload(source_calendar.id)
    )
    event_id = create.json()["id"]

    resp = await async_client.delete(f"/api/events/{event_id}")
    assert resp.status_code == 204


async def test_event_not_found(async_client: AsyncClient) -> None:
    fake_id = uuid.uuid4()
    resp = await async_client.get(f"/api/events/{fake_id}")
    assert resp.status_code == 404
