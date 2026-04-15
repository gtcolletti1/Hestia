"""Tests for server-side RRULE expansion in the events endpoint."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient


@pytest.fixture
async def sample_calendar(authed_client: AsyncClient, sample_household):
    """Create a source calendar for test events."""
    resp = await authed_client.post(
        "/api/calendars",
        json={
            "name": "Test Cal",
            "provider": "local",
            "household_id": str(sample_household.id),
        },
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.mark.asyncio
async def test_daily_recurrence_expansion(authed_client: AsyncClient, sample_household, sample_calendar):
    """A daily recurring event should produce occurrences within the queried range."""
    start = datetime(2026, 4, 1, 9, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)

    resp = await authed_client.post(
        "/api/events",
        json={
            "title": "Daily Standup",
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "source_calendar_id": sample_calendar["id"],
            "recurrence_rule": "RRULE:FREQ=DAILY;COUNT=10",
        },
    )
    assert resp.status_code == 201

    # Query a 5-day window → should get 5 occurrences
    list_resp = await authed_client.get(
        "/api/events",
        params={
            "household_id": str(sample_household.id),
            "start_date": "2026-04-01",
            "end_date": "2026-04-05",
        },
    )
    assert list_resp.status_code == 200
    events = list_resp.json()
    standup_events = [e for e in events if e["title"] == "Daily Standup"]
    assert len(standup_events) == 5


@pytest.mark.asyncio
async def test_weekly_recurrence_expansion(authed_client: AsyncClient, sample_household, sample_calendar):
    """A weekly recurring event should appear once per week."""
    start = datetime(2026, 4, 6, 18, 0, tzinfo=timezone.utc)  # Monday
    end = start + timedelta(hours=2)

    resp = await authed_client.post(
        "/api/events",
        json={
            "title": "Family Game Night",
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "source_calendar_id": sample_calendar["id"],
            "recurrence_rule": "RRULE:FREQ=WEEKLY",
        },
    )
    assert resp.status_code == 201

    # Query a 3-week window → should get 3 occurrences
    list_resp = await authed_client.get(
        "/api/events",
        params={
            "household_id": str(sample_household.id),
            "start_date": "2026-04-06",
            "end_date": "2026-04-26",
        },
    )
    assert list_resp.status_code == 200
    events = list_resp.json()
    game_events = [e for e in events if e["title"] == "Family Game Night"]
    assert len(game_events) == 3


@pytest.mark.asyncio
async def test_monthly_recurrence_expansion(authed_client: AsyncClient, sample_household, sample_calendar):
    """A monthly recurring event should appear once per month."""
    start = datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)

    resp = await authed_client.post(
        "/api/events",
        json={
            "title": "Monthly Review",
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "source_calendar_id": sample_calendar["id"],
            "recurrence_rule": "RRULE:FREQ=MONTHLY",
        },
    )
    assert resp.status_code == 201

    # Query Jan-Apr → should get 4 occurrences
    list_resp = await authed_client.get(
        "/api/events",
        params={
            "household_id": str(sample_household.id),
            "start_date": "2026-01-01",
            "end_date": "2026-04-30",
        },
    )
    assert list_resp.status_code == 200
    events = list_resp.json()
    review_events = [e for e in events if e["title"] == "Monthly Review"]
    assert len(review_events) == 4


@pytest.mark.asyncio
async def test_recurrence_preserves_duration(authed_client: AsyncClient, sample_household, sample_calendar):
    """Each occurrence should have the same duration as the original event."""
    start = datetime(2026, 4, 1, 14, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=2, minutes=30)

    resp = await authed_client.post(
        "/api/events",
        json={
            "title": "Long Meeting",
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "source_calendar_id": sample_calendar["id"],
            "recurrence_rule": "RRULE:FREQ=DAILY;COUNT=3",
        },
    )
    assert resp.status_code == 201

    list_resp = await authed_client.get(
        "/api/events",
        params={
            "household_id": str(sample_household.id),
            "start_date": "2026-04-01",
            "end_date": "2026-04-03",
        },
    )
    assert list_resp.status_code == 200
    events = list_resp.json()
    meetings = [e for e in events if e["title"] == "Long Meeting"]
    for meeting in meetings:
        s = datetime.fromisoformat(meeting["start_time"])
        e = datetime.fromisoformat(meeting["end_time"])
        assert (e - s) == timedelta(hours=2, minutes=30)


@pytest.mark.asyncio
async def test_non_recurring_events_unaffected(authed_client: AsyncClient, sample_household, sample_calendar):
    """Non-recurring events should still be returned normally."""
    start = datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)

    resp = await authed_client.post(
        "/api/events",
        json={
            "title": "One-off Lunch",
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "source_calendar_id": sample_calendar["id"],
        },
    )
    assert resp.status_code == 201

    list_resp = await authed_client.get(
        "/api/events",
        params={
            "household_id": str(sample_household.id),
            "start_date": "2026-04-01",
            "end_date": "2026-04-30",
        },
    )
    assert list_resp.status_code == 200
    events = list_resp.json()
    lunch_events = [e for e in events if e["title"] == "One-off Lunch"]
    assert len(lunch_events) == 1


@pytest.mark.asyncio
async def test_malformed_rrule_returns_original(authed_client: AsyncClient, sample_household, sample_calendar):
    """A malformed RRULE should gracefully return the original event."""
    start = datetime(2026, 4, 5, 9, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)

    resp = await authed_client.post(
        "/api/events",
        json={
            "title": "Bad Rule Event",
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "source_calendar_id": sample_calendar["id"],
            "recurrence_rule": "NOT_A_VALID_RRULE",
        },
    )
    assert resp.status_code == 201

    list_resp = await authed_client.get(
        "/api/events",
        params={
            "household_id": str(sample_household.id),
            "start_date": "2026-04-01",
            "end_date": "2026-04-30",
        },
    )
    assert list_resp.status_code == 200
    events = list_resp.json()
    bad_events = [e for e in events if e["title"] == "Bad Rule Event"]
    # Should still get the original event (graceful degradation)
    assert len(bad_events) >= 1
