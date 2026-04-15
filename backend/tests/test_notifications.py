"""Tests for the reminders and notifications API endpoints."""

import uuid
import datetime as dt

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calendar import Event, SourceCalendar
from app.models.user import Household, Profile


# ── Helper to create an event for testing ────────────────────────────────────

async def _create_event(db: AsyncSession, household: Household, profile: Profile, start_offset_hours: int = 1) -> Event:
    """Create a source calendar and event for testing."""
    cal = SourceCalendar(
        household_id=household.id,
        name="Test Cal",
        provider="local",
        external_id=f"test-cal-{uuid.uuid4()}",
    )
    db.add(cal)
    await db.flush()

    now = dt.datetime.utcnow()
    event = Event(
        source_calendar_id=cal.id,
        title="Test Event",
        start_time=now + dt.timedelta(hours=start_offset_hours),
        end_time=now + dt.timedelta(hours=start_offset_hours + 1),
        external_id=f"evt-{uuid.uuid4()}",
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event


# ── Unauthenticated access ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reminders_create_requires_auth(async_client: AsyncClient, sample_household: Household):
    resp = await async_client.post("/api/reminders", json={
        "event_id": str(uuid.uuid4()),
        "minutes_before": 15,
        "household_id": str(sample_household.id),
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_notifications_requires_auth(async_client: AsyncClient, sample_household: Household):
    resp = await async_client.get("/api/notifications/upcoming", params={
        "household_id": str(sample_household.id),
    })
    assert resp.status_code == 401


# ── Create & list reminders ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_reminder(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
    db_session: AsyncSession,
):
    event = await _create_event(db_session, sample_household, sample_profile)

    resp = await authed_client.post("/api/reminders", json={
        "event_id": str(event.id),
        "minutes_before": 15,
        "household_id": str(sample_household.id),
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["minutes_before"] == 15
    assert data["is_fired"] is False
    assert data["event_id"] == str(event.id)


@pytest.mark.asyncio
async def test_list_reminders_for_event(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
    db_session: AsyncSession,
):
    event = await _create_event(db_session, sample_household, sample_profile)

    # Create two reminders
    await authed_client.post("/api/reminders", json={
        "event_id": str(event.id),
        "minutes_before": 15,
        "household_id": str(sample_household.id),
    })
    await authed_client.post("/api/reminders", json={
        "event_id": str(event.id),
        "minutes_before": 60,
        "household_id": str(sample_household.id),
    })

    resp = await authed_client.get("/api/reminders", params={
        "event_id": str(event.id),
        "household_id": str(sample_household.id),
    })
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_delete_reminder(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
    db_session: AsyncSession,
):
    event = await _create_event(db_session, sample_household, sample_profile)

    resp = await authed_client.post("/api/reminders", json={
        "event_id": str(event.id),
        "minutes_before": 30,
        "household_id": str(sample_household.id),
    })
    reminder_id = resp.json()["id"]

    resp = await authed_client.delete(f"/api/reminders/{reminder_id}")
    assert resp.status_code == 204


# ── Upcoming notifications ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upcoming_notifications_fires(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
    db_session: AsyncSession,
):
    # Create event starting in 10 minutes with a 15-min reminder (fire_at = -5min = past)
    now = dt.datetime.utcnow()
    cal = SourceCalendar(
        household_id=sample_household.id,
        name="Notif Cal",
        provider="local",
        external_id=f"notif-cal-{uuid.uuid4()}",
    )
    db_session.add(cal)
    await db_session.flush()

    event = Event(
        source_calendar_id=cal.id,
        title="Meeting Soon",
        start_time=now + dt.timedelta(minutes=10),
        end_time=now + dt.timedelta(minutes=40),
        external_id=f"evt-notif-{uuid.uuid4()}",
    )
    db_session.add(event)
    await db_session.flush()
    await db_session.refresh(event)

    # Create reminder that should fire now (fire_at = start - 15min = now - 5min)
    await authed_client.post("/api/reminders", json={
        "event_id": str(event.id),
        "minutes_before": 15,
        "household_id": str(sample_household.id),
    })

    resp = await authed_client.get("/api/notifications/upcoming", params={
        "household_id": str(sample_household.id),
    })
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["event_title"] == "Meeting Soon"

    # Second poll should return empty (already fired)
    resp = await authed_client.get("/api/notifications/upcoming", params={
        "household_id": str(sample_household.id),
    })
    assert len(resp.json()) == 0


# ── Cross-household ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reminders_cross_household_denied(
    authed_client: AsyncClient,
    second_household: Household,
    second_profile: Profile,
):
    resp = await authed_client.post("/api/reminders", json={
        "event_id": str(uuid.uuid4()),
        "minutes_before": 15,
        "household_id": str(second_household.id),
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_notifications_cross_household_denied(
    authed_client: AsyncClient,
    second_household: Household,
    second_profile: Profile,
):
    resp = await authed_client.get("/api/notifications/upcoming", params={
        "household_id": str(second_household.id),
    })
    assert resp.status_code == 403


# ── 404 handling ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_reminder_event_not_found(authed_client: AsyncClient, sample_household: Household):
    resp = await authed_client.post("/api/reminders", json={
        "event_id": "00000000-0000-0000-0000-000000000000",
        "minutes_before": 15,
        "household_id": str(sample_household.id),
    })
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_reminder_not_found(authed_client: AsyncClient):
    resp = await authed_client.delete("/api/reminders/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
