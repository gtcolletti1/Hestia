"""Tests for the Dashboard composite endpoint."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Household, Profile

pytestmark = pytest.mark.asyncio


# ── Tests ────────────────────────────────────────────────────────────────────


async def test_dashboard_shape(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    resp = await authed_client.get(
        "/api/dashboard",
        params={"household_id": str(sample_household.id)},
    )
    assert resp.status_code == 200
    body = resp.json()

    # All 6 top-level keys present
    for key in ("date", "profiles", "agenda", "active_routines", "today_meals", "active_lists"):
        assert key in body, f"Missing key: {key}"

    # Agenda has exactly 3 buckets
    assert isinstance(body["agenda"], list)
    assert len(body["agenda"]) == 3
    bucket_names = [b["bucket"] for b in body["agenda"]]
    assert bucket_names == ["morning", "afternoon", "evening"]

    for bucket in body["agenda"]:
        assert "events" in bucket
        assert isinstance(bucket["events"], list)


async def test_dashboard_includes_profiles(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    resp = await authed_client.get(
        "/api/dashboard",
        params={"household_id": str(sample_household.id)},
    )
    assert resp.status_code == 200
    profiles = resp.json()["profiles"]

    profile_ids = [p["id"] for p in profiles]
    assert str(sample_profile.id) in profile_ids

    matched = next(p for p in profiles if p["id"] == str(sample_profile.id))
    assert matched["name"] == sample_profile.name
    assert "color" in matched


async def test_dashboard_includes_lists(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    # Create a list with 2 items
    list_resp = await authed_client.post(
        "/api/lists",
        json={
            "household_id": str(sample_household.id),
            "name": "Dashboard Test List",
            "category": "todo",
        },
    )
    assert list_resp.status_code == 201
    list_id = list_resp.json()["id"]

    await authed_client.post(
        f"/api/lists/{list_id}/items",
        json={"text": "Item A", "sort_order": 0},
    )
    item2_resp = await authed_client.post(
        f"/api/lists/{list_id}/items",
        json={"text": "Item B", "sort_order": 1},
    )
    item2_id = item2_resp.json()["id"]

    # Check one item
    await authed_client.patch(f"/api/lists/{list_id}/items/{item2_id}/toggle")

    # Fetch dashboard
    resp = await authed_client.get(
        "/api/dashboard",
        params={"household_id": str(sample_household.id)},
    )
    assert resp.status_code == 200
    active_lists = resp.json()["active_lists"]

    matched = [al for al in active_lists if al["id"] == list_id]
    assert len(matched) == 1
    assert matched[0]["name"] == "Dashboard Test List"
    assert matched[0]["item_count"] == 2
    assert matched[0]["checked_count"] == 1


async def test_dashboard_requires_auth(
    async_client: AsyncClient, sample_household: Household
) -> None:
    resp = await async_client.get(
        "/api/dashboard",
        params={"household_id": str(sample_household.id)},
    )
    assert resp.status_code in (401, 403)
