"""Tests for the profiles & households API."""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.models.user import Household, Profile, ProfileRole

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
    authed_client: AsyncClient, sample_household: Household, sample_profile: Profile
) -> None:
    payload = {
        "name": "Jane",
        "color": "#00FF00",
        "role": "standard",
        "household_id": str(sample_household.id),
    }
    resp = await authed_client.post("/api/profiles", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Jane"
    assert body["color"] == "#00FF00"
    assert body["household_id"] == str(sample_household.id)
    assert body["is_active"] is True


async def test_create_first_profile_bootstrap_admin(
    async_client: AsyncClient, db_session,
) -> None:
    """The very first profile in an empty household may be created without auth,
    but must be an admin (the bootstrap path used by the setup wizard)."""
    household = Household(name="Bootstrap Family")
    db_session.add(household)
    await db_session.flush()
    await db_session.refresh(household)

    # Standard role on bootstrap is rejected
    bad = await async_client.post(
        "/api/profiles",
        json={
            "name": "NotAdmin",
            "color": "#123456",
            "role": "standard",
            "household_id": str(household.id),
        },
    )
    assert bad.status_code == 400

    # Admin role on bootstrap succeeds
    good = await async_client.post(
        "/api/profiles",
        json={
            "name": "FirstAdmin",
            "color": "#123456",
            "role": "admin",
            "household_id": str(household.id),
        },
    )
    assert good.status_code == 201

    # Subsequent unauth POST is now blocked
    blocked = await async_client.post(
        "/api/profiles",
        json={
            "name": "Second",
            "color": "#654321",
            "role": "standard",
            "household_id": str(household.id),
        },
    )
    assert blocked.status_code == 401


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
    authed_client: AsyncClient, sample_profile: Profile
) -> None:
    resp = await authed_client.put(
        f"/api/profiles/{sample_profile.id}",
        json={"name": "Updated Name", "color": "#000000"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Updated Name"
    assert body["color"] == "#000000"


async def test_delete_profile(
    authed_client: AsyncClient, async_client: AsyncClient, sample_household: Household
) -> None:
    # Create a disposable profile via authed_client (non-bootstrap path), then delete it
    create_resp = await authed_client.post(
        "/api/profiles",
        json={
            "name": "ToDelete",
            "color": "#111111",
            "household_id": str(sample_household.id),
        },
    )
    assert create_resp.status_code == 201
    profile_id = create_resp.json()["id"]

    resp = await authed_client.delete(f"/api/profiles/{profile_id}")
    assert resp.status_code == 204

    # Confirm it's gone
    get_resp = await async_client.get(f"/api/profiles/{profile_id}")
    assert get_resp.status_code == 404


async def test_get_nonexistent_profile(async_client: AsyncClient) -> None:
    fake_id = uuid.uuid4()
    resp = await async_client.get(f"/api/profiles/{fake_id}")
    assert resp.status_code == 404
