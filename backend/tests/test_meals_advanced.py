"""Advanced meal planning tests — duplicate constraint, weekly view, fields.

PRD refs: US-2.6.1 (one meal per household/date/meal_type), US-2.6.2 (weekly grid).
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.models.user import Household, Profile

pytestmark = pytest.mark.asyncio


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _create_meal(
    client: AsyncClient, household_id: str, **kwargs
) -> dict:
    payload = {"household_id": household_id, **kwargs}
    resp = await client.post("/api/meals", json=payload)
    return resp


# ── Tests ────────────────────────────────────────────────────────────────────


async def test_duplicate_meal_same_day_type_rejected(
    authed_client: AsyncClient,
    sample_household: Household,
) -> None:
    """Creating two meals for the same (household, date, meal_type) returns 409."""
    hid = str(sample_household.id)

    # First: succeeds
    resp1 = await _create_meal(
        authed_client, hid, date="2024-09-01", meal_type="dinner", title="Tacos"
    )
    assert resp1.status_code == 201

    # Second: same date+type → conflict
    resp2 = await _create_meal(
        authed_client, hid, date="2024-09-01", meal_type="dinner", title="Burgers"
    )
    assert resp2.status_code == 409
    assert "already exists" in resp2.json()["detail"].lower()


async def test_different_meal_types_same_day_allowed(
    authed_client: AsyncClient,
    sample_household: Household,
) -> None:
    """Different meal types on the same day are allowed."""
    hid = str(sample_household.id)

    r1 = await _create_meal(
        authed_client, hid, date="2024-09-02", meal_type="breakfast", title="Eggs"
    )
    assert r1.status_code == 201

    r2 = await _create_meal(
        authed_client, hid, date="2024-09-02", meal_type="lunch", title="Soup"
    )
    assert r2.status_code == 201

    r3 = await _create_meal(
        authed_client, hid, date="2024-09-02", meal_type="dinner", title="Steak"
    )
    assert r3.status_code == 201


async def test_meal_with_recipe_url(
    authed_client: AsyncClient,
    sample_household: Household,
) -> None:
    """recipe_url is persisted and returned."""
    hid = str(sample_household.id)
    resp = await _create_meal(
        authed_client, hid,
        date="2024-09-03", meal_type="dinner", title="Pad Thai",
        recipe_url="https://example.com/pad-thai",
    )
    assert resp.status_code == 201
    assert resp.json()["recipe_url"] == "https://example.com/pad-thai"


async def test_meal_with_description(
    authed_client: AsyncClient,
    sample_household: Household,
) -> None:
    """description is persisted."""
    hid = str(sample_household.id)
    resp = await _create_meal(
        authed_client, hid,
        date="2024-09-04", meal_type="breakfast", title="Smoothie",
        description="Banana, strawberry, yogurt",
    )
    assert resp.status_code == 201
    assert resp.json()["description"] == "Banana, strawberry, yogurt"


async def test_meal_with_assigned_profile(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """assigned_profile_id (who's cooking) is persisted."""
    hid = str(sample_household.id)
    pid = str(sample_profile.id)

    resp = await _create_meal(
        authed_client, hid,
        date="2024-09-05", meal_type="dinner", title="Pasta",
        assigned_profile_id=pid,
    )
    assert resp.status_code == 201
    assert resp.json()["assigned_profile_id"] == pid


async def test_weekly_view_7_days(
    authed_client: AsyncClient,
    sample_household: Household,
) -> None:
    """Weekly view returns exactly 7 days with meals correctly placed."""
    hid = str(sample_household.id)
    await _create_meal(
        authed_client, hid, date="2024-09-09", meal_type="breakfast", title="Cereal"
    )
    await _create_meal(
        authed_client, hid, date="2024-09-11", meal_type="dinner", title="Fish"
    )

    resp = await authed_client.get(
        "/api/meals/week",
        params={"household_id": hid, "week_start": "2024-09-09"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["days"]) == 7

    # Monday (index 0) has breakfast
    mon_titles = [m["title"] for m in body["days"][0]["meals"]]
    assert "Cereal" in mon_titles

    # Wednesday (index 2) has dinner
    wed_titles = [m["title"] for m in body["days"][2]["meals"]]
    assert "Fish" in wed_titles


async def test_edit_meal_replaces_data(
    authed_client: AsyncClient,
    sample_household: Household,
) -> None:
    """PUT replaces meal data cleanly."""
    hid = str(sample_household.id)
    resp = await _create_meal(
        authed_client, hid, date="2024-09-06", meal_type="lunch", title="Old Title"
    )
    meal_id = resp.json()["id"]

    resp = await authed_client.put(
        f"/api/meals/{meal_id}",
        json={"title": "New Title", "description": "Updated desc"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "New Title"
    assert resp.json()["description"] == "Updated desc"
