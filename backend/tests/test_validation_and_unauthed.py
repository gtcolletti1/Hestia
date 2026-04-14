"""Tests for unauthenticated access and input validation."""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.models.user import Household

pytestmark = pytest.mark.asyncio


# ── Unauthenticated access tests ─────────────────────────────────────────────
# These verify that endpoints reject requests without a valid JWT.


async def test_unauthed_list_events(async_client: AsyncClient) -> None:
    resp = await async_client.get(
        "/api/events",
        params={
            "household_id": str(uuid.uuid4()),
            "start_date": "2024-06-01",
            "end_date": "2024-06-07",
        },
    )
    assert resp.status_code in (401, 403)


async def test_unauthed_list_routines(async_client: AsyncClient) -> None:
    resp = await async_client.get(
        "/api/routines",
        params={"household_id": str(uuid.uuid4())},
    )
    assert resp.status_code in (401, 403)


async def test_unauthed_list_lists(async_client: AsyncClient) -> None:
    resp = await async_client.get(
        "/api/lists",
        params={"household_id": str(uuid.uuid4())},
    )
    assert resp.status_code in (401, 403)


async def test_unauthed_create_meal(async_client: AsyncClient) -> None:
    resp = await async_client.post(
        "/api/meals",
        json={
            "household_id": str(uuid.uuid4()),
            "date": "2024-06-01",
            "meal_type": "breakfast",
            "title": "Test",
        },
    )
    assert resp.status_code in (401, 403)


async def test_unauthed_trigger_sync(async_client: AsyncClient) -> None:
    resp = await async_client.get(
        f"/api/integrations/calendars/sync/{uuid.uuid4()}",
    )
    assert resp.status_code in (401, 403)


async def test_unauthed_integration_status(async_client: AsyncClient) -> None:
    resp = await async_client.get(
        "/api/integrations/status",
        params={"household_id": str(uuid.uuid4())},
    )
    assert resp.status_code in (401, 403)


async def test_unauthed_set_pin(async_client: AsyncClient) -> None:
    resp = await async_client.post(
        "/api/auth/pin",
        json={"profile_id": str(uuid.uuid4()), "pin": "1234"},
    )
    assert resp.status_code in (401, 403)


# ── Input validation tests ───────────────────────────────────────────────────


async def test_create_meal_invalid_meal_type(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    """Invalid meal_type should be rejected."""
    resp = await authed_client.post(
        "/api/meals",
        json={
            "household_id": str(sample_household.id),
            "date": "2024-06-01",
            "meal_type": "brunch",
            "title": "Invalid",
        },
    )
    assert resp.status_code == 422


async def test_create_meal_missing_title(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    """Missing required field should return 422."""
    resp = await authed_client.post(
        "/api/meals",
        json={
            "household_id": str(sample_household.id),
            "date": "2024-06-01",
            "meal_type": "breakfast",
        },
    )
    assert resp.status_code == 422


async def test_create_routine_invalid_time_block(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    """Invalid time_block should be rejected."""
    resp = await authed_client.post(
        "/api/routines",
        json={
            "household_id": str(sample_household.id),
            "name": "Bad Routine",
            "time_block": "midnight",
            "days_of_week": [0],
            "steps": [{"label": "Step", "icon": "✅", "sort_order": 0}],
        },
    )
    assert resp.status_code == 422


async def test_create_list_missing_name(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    """Missing required 'name' field should return 422."""
    resp = await authed_client.post(
        "/api/lists",
        json={
            "household_id": str(sample_household.id),
            "category": "todo",
        },
    )
    assert resp.status_code == 422


async def test_get_nonexistent_routine(
    authed_client: AsyncClient,
) -> None:
    """Getting a non-existent routine returns 404."""
    resp = await authed_client.get(f"/api/routines/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_get_nonexistent_calendar(
    authed_client: AsyncClient,
) -> None:
    """Updating a non-existent calendar returns 404."""
    resp = await authed_client.put(
        f"/api/calendars/{uuid.uuid4()}",
        json={"name": "Ghost Calendar"},
    )
    assert resp.status_code == 404


async def test_delete_nonexistent_meal(
    authed_client: AsyncClient,
) -> None:
    """Deleting a non-existent meal returns 404."""
    resp = await authed_client.delete(f"/api/meals/{uuid.uuid4()}")
    assert resp.status_code == 404
