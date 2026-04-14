"""Cross-household access tests for meals endpoints."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models.user import Household

pytestmark = pytest.mark.asyncio


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _create_meal(client: AsyncClient, household_id: str) -> str:
    """Create a meal in the given household. Returns meal_id."""
    resp = await client.post(
        "/api/meals",
        json={
            "household_id": household_id,
            "date": "2024-06-01",
            "meal_type": "breakfast",
            "title": "Pancakes",
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# ── Cross-household tests ────────────────────────────────────────────────────


async def test_cross_household_list_meals(
    authed_client: AsyncClient,
    second_authed_client: AsyncClient,
    sample_household: Household,
) -> None:
    """User from household B cannot list household A's meals."""
    resp = await second_authed_client.get(
        "/api/meals",
        params={"household_id": str(sample_household.id), "date": "2024-06-01"},
    )
    assert resp.status_code == 403


async def test_cross_household_get_weekly_meals(
    authed_client: AsyncClient,
    second_authed_client: AsyncClient,
    sample_household: Household,
) -> None:
    """User from household B cannot view household A's weekly meals."""
    resp = await second_authed_client.get(
        "/api/meals/week",
        params={"household_id": str(sample_household.id), "week_start": "2024-06-01"},
    )
    assert resp.status_code == 403


async def test_cross_household_get_meal(
    authed_client: AsyncClient,
    second_authed_client: AsyncClient,
    sample_household: Household,
) -> None:
    """User from household B cannot get a specific meal from household A."""
    meal_id = await _create_meal(authed_client, str(sample_household.id))

    resp = await second_authed_client.get(f"/api/meals/{meal_id}")
    assert resp.status_code == 403


async def test_cross_household_create_meal(
    second_authed_client: AsyncClient,
    sample_household: Household,
) -> None:
    """User from household B cannot create a meal in household A."""
    resp = await second_authed_client.post(
        "/api/meals",
        json={
            "household_id": str(sample_household.id),
            "date": "2024-06-01",
            "meal_type": "lunch",
            "title": "Hacked Lunch",
        },
    )
    assert resp.status_code == 403


async def test_cross_household_update_meal(
    authed_client: AsyncClient,
    second_authed_client: AsyncClient,
    sample_household: Household,
) -> None:
    """User from household B cannot update household A's meal."""
    meal_id = await _create_meal(authed_client, str(sample_household.id))

    resp = await second_authed_client.put(
        f"/api/meals/{meal_id}",
        json={"title": "Tampered Meal"},
    )
    assert resp.status_code == 403


async def test_cross_household_delete_meal(
    authed_client: AsyncClient,
    second_authed_client: AsyncClient,
    sample_household: Household,
) -> None:
    """User from household B cannot delete household A's meal."""
    meal_id = await _create_meal(authed_client, str(sample_household.id))

    resp = await second_authed_client.delete(f"/api/meals/{meal_id}")
    assert resp.status_code == 403
