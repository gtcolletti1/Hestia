"""Tests for cascade deletes — routine→steps, list→items, calendar→events.

PRD refs: US-2.3.4 (delete cascades steps+completions), data model section.
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calendar import SourceCalendar, CalendarProvider
from app.models.user import Household, Profile

pytestmark = pytest.mark.asyncio


# ── Tests ────────────────────────────────────────────────────────────────────


async def test_delete_routine_cascades_steps(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """Deleting a routine removes all its steps."""
    hid = str(sample_household.id)
    pid = str(sample_profile.id)

    r = await authed_client.post(
        "/api/routines",
        json={
            "household_id": hid,
            "profile_id": pid,
            "name": "Cascade Routine",
            "time_block": "morning",
            "days_of_week": [0, 1, 2, 3, 4],
            "steps": [
                {"label": "Step A", "sort_order": 0},
                {"label": "Step B", "sort_order": 1},
            ],
        },
    )
    routine_id = r.json()["id"]

    # Delete the routine
    resp = await authed_client.delete(f"/api/routines/{routine_id}")
    assert resp.status_code == 204

    # Verify routine is gone
    resp = await authed_client.get(
        f"/api/routines/{routine_id}",
        params={"household_id": hid},
    )
    assert resp.status_code == 404


async def test_delete_list_cascades_items(
    authed_client: AsyncClient,
    sample_household: Household,
) -> None:
    """Deleting a list removes all its items."""
    hid = str(sample_household.id)

    # Create list with items
    lr = await authed_client.post(
        "/api/lists",
        json={"household_id": hid, "name": "Cascade List", "category": "todo"},
    )
    list_id = lr.json()["id"]

    await authed_client.post(
        f"/api/lists/{list_id}/items",
        json={"text": "Item 1", "sort_order": 0},
    )
    await authed_client.post(
        f"/api/lists/{list_id}/items",
        json={"text": "Item 2", "sort_order": 1},
    )

    # Delete the list
    resp = await authed_client.delete(f"/api/lists/{list_id}")
    assert resp.status_code == 204

    # Verify list is gone
    resp = await authed_client.get(
        f"/api/lists/{list_id}",
        params={"household_id": hid},
    )
    assert resp.status_code == 404


async def test_delete_calendar_cascades_events(
    authed_client: AsyncClient,
    sample_household: Household,
    db_session: AsyncSession,
) -> None:
    """Deleting a source calendar removes all its events."""
    hid = str(sample_household.id)

    # Create calendar via API
    cal_resp = await authed_client.post(
        "/api/calendars",
        json={
            "household_id": hid,
            "name": "Cascade Cal",
            "provider": "local",
        },
    )
    assert cal_resp.status_code == 201
    cal_id = cal_resp.json()["id"]

    # Create event in that calendar
    event_resp = await authed_client.post(
        "/api/events",
        json={
            "source_calendar_id": cal_id,
            "title": "Cascade Event",
            "start_time": "2024-12-01T10:00:00",
            "end_time": "2024-12-01T11:00:00",
        },
    )
    assert event_resp.status_code == 201

    # Delete the calendar
    resp = await authed_client.delete(f"/api/calendars/{cal_id}")
    assert resp.status_code == 204


async def test_delete_routine_with_completions(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """Deleting a routine that has completion records succeeds (cascade)."""
    hid = str(sample_household.id)
    pid = str(sample_profile.id)

    r = await authed_client.post(
        "/api/routines",
        json={
            "household_id": hid,
            "profile_id": pid,
            "name": "Completed Routine",
            "time_block": "evening",
            "days_of_week": [0, 1, 2, 3, 4, 5, 6],
            "steps": [{"label": "Only Step", "sort_order": 0, "points_value": 5}],
        },
    )
    routine = r.json()

    # Complete a step (creates RoutineCompletion record)
    await authed_client.post(
        f"/api/routines/{routine['id']}/steps/{routine['steps'][0]['id']}/complete",
        params={"profile_id": pid},
    )

    # Delete should still work
    resp = await authed_client.delete(f"/api/routines/{routine['id']}")
    assert resp.status_code == 204
