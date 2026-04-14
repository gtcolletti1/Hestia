"""Tests for the Meals API."""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Household, Profile

pytestmark = pytest.mark.asyncio


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _create_meal(
    client: AsyncClient, household_id: str, *, date: str, meal_type: str, title: str
) -> dict:
    resp = await client.post(
        "/api/meals",
        json={
            "household_id": household_id,
            "date": date,
            "meal_type": meal_type,
            "title": title,
        },
    )
    assert resp.status_code == 201
    return resp.json()


# ── Tests ────────────────────────────────────────────────────────────────────


async def test_create_meal(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    resp = await authed_client.post(
        "/api/meals",
        json={
            "household_id": str(sample_household.id),
            "date": "2024-06-01",
            "meal_type": "breakfast",
            "title": "Pancakes",
            "description": "With maple syrup",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Pancakes"
    assert body["meal_type"] == "breakfast"
    assert body["date"] == "2024-06-01"
    assert body["household_id"] == str(sample_household.id)
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body


async def test_list_meals_by_date(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    hid = str(sample_household.id)
    await _create_meal(authed_client, hid, date="2024-06-15", meal_type="breakfast", title="Oatmeal")
    await _create_meal(authed_client, hid, date="2024-06-15", meal_type="lunch", title="Sandwich")

    resp = await authed_client.get(
        "/api/meals",
        params={"household_id": hid, "date": "2024-06-15"},
    )
    assert resp.status_code == 200
    meals = resp.json()
    assert len(meals) == 2
    titles = {m["title"] for m in meals}
    assert titles == {"Oatmeal", "Sandwich"}


async def test_get_weekly_view_shape(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    hid = str(sample_household.id)
    await _create_meal(authed_client, hid, date="2024-07-01", meal_type="breakfast", title="Eggs")
    await _create_meal(authed_client, hid, date="2024-07-03", meal_type="dinner", title="Pasta")

    resp = await authed_client.get(
        "/api/meals/week",
        params={"household_id": hid, "week_start": "2024-07-01"},
    )
    assert resp.status_code == 200
    body = resp.json()

    assert isinstance(body["week_start"], str)
    assert body["week_start"] == "2024-07-01"
    assert isinstance(body["days"], list)
    assert len(body["days"]) == 7

    for day in body["days"]:
        assert "date" in day
        assert "meals" in day
        assert isinstance(day["meals"], list)

    # Day 0 (July 1) should have the breakfast
    assert any(m["title"] == "Eggs" for m in body["days"][0]["meals"])
    # Day 2 (July 3) should have the dinner
    assert any(m["title"] == "Pasta" for m in body["days"][2]["meals"])


async def test_update_meal(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    hid = str(sample_household.id)
    meal = await _create_meal(authed_client, hid, date="2024-08-01", meal_type="dinner", title="Tacos")

    resp = await authed_client.put(
        f"/api/meals/{meal['id']}",
        json={"title": "Fish Tacos"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Fish Tacos"


async def test_delete_meal(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    hid = str(sample_household.id)
    meal = await _create_meal(authed_client, hid, date="2024-08-10", meal_type="snack", title="Yogurt")

    resp = await authed_client.delete(f"/api/meals/{meal['id']}")
    assert resp.status_code == 204

    resp = await authed_client.get(f"/api/meals/{meal['id']}")
    assert resp.status_code == 404


async def test_meals_require_auth(
    async_client: AsyncClient, sample_household: Household
) -> None:
    resp = await async_client.get(
        "/api/meals",
        params={"household_id": str(sample_household.id)},
    )
    assert resp.status_code in (401, 403)


async def test_meal_not_found(authed_client: AsyncClient) -> None:
    fake_id = str(uuid.uuid4())
    resp = await authed_client.get(f"/api/meals/{fake_id}")
    assert resp.status_code == 404
