"""Tests for the profiles & households API."""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.models.user import Household, Profile

pytestmark = pytest.mark.asyncio


# ── Households ───────────────────────────────────────────────────────────────


async def test_create_household(async_client: AsyncClient) -> None:
    resp = await async_client.post("/api/households", json={"name": "Smith Family"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Smith Family"
    assert "id" in body
    assert "created_at" in body
    assert "profiles" in body


# ── Create / Read / Update / Delete profiles ─────────────────────────────────


async def test_create_profile(
    async_client: AsyncClient, sample_household: Household
) -> None:
    payload = {
        "name": "Jane",
        "color": "#00FF00",
        "role": "standard",
        "household_id": str(sample_household.id),
    }
    resp = await async_client.post("/api/profiles", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Jane"
    assert body["color"] == "#00FF00"
    assert body["household_id"] == str(sample_household.id)
    assert body["is_active"] is True


async def test_list_profiles(
    async_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    resp = await async_client.get(
        "/api/profiles", params={"household_id": str(sample_household.id)}
    )
    assert resp.status_code == 200
    profiles = resp.json()
    assert isinstance(profiles, list)
    assert len(profiles) >= 1
    ids = [p["id"] for p in profiles]
    assert str(sample_profile.id) in ids


async def test_get_profile(
    async_client: AsyncClient, sample_profile: Profile
) -> None:
    resp = await async_client.get(f"/api/profiles/{sample_profile.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(sample_profile.id)
    assert body["name"] == sample_profile.name


async def test_update_profile(
    async_client: AsyncClient, sample_profile: Profile
) -> None:
    resp = await async_client.put(
        f"/api/profiles/{sample_profile.id}",
        json={"name": "Updated Name", "color": "#000000"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Updated Name"
    assert body["color"] == "#000000"


async def test_delete_profile(
    async_client: AsyncClient, sample_household: Household
) -> None:
    # Create a disposable profile, then delete it
    create_resp = await async_client.post(
        "/api/profiles",
        json={
            "name": "ToDelete",
            "color": "#111111",
            "household_id": str(sample_household.id),
        },
    )
    profile_id = create_resp.json()["id"]

    resp = await async_client.delete(f"/api/profiles/{profile_id}")
    assert resp.status_code == 204

    # Confirm it's gone
    get_resp = await async_client.get(f"/api/profiles/{profile_id}")
    assert get_resp.status_code == 404


async def test_get_nonexistent_profile(async_client: AsyncClient) -> None:
    fake_id = uuid.uuid4()
    resp = await async_client.get(f"/api/profiles/{fake_id}")
    assert resp.status_code == 404
