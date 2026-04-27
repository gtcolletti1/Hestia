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
    """List endpoint is intentionally unauthenticated — needed pre-login
    to render the profile selector tiles."""
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
    authed_client: AsyncClient, sample_profile: Profile
) -> None:
    resp = await authed_client.get(f"/api/profiles/{sample_profile.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(sample_profile.id)
    assert body["name"] == sample_profile.name


async def test_get_profile_requires_auth(
    async_client: AsyncClient, sample_profile: Profile
) -> None:
    resp = await async_client.get(f"/api/profiles/{sample_profile.id}")
    assert resp.status_code == 401


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


async def test_update_profile_pin_is_hashed_and_authenticates(
    authed_client: AsyncClient, async_client: AsyncClient, sample_profile: Profile, db_session
) -> None:
    """Regression: PUT /profiles must hash a new pin into pin_hash so the
    user can subsequently log in with it. Previously the schema dropped the
    field silently and the handler did setattr(profile, 'pin', ...)."""
    new_pin = "9911"
    resp = await authed_client.put(
        f"/api/profiles/{sample_profile.id}",
        json={"pin": new_pin},
    )
    assert resp.status_code == 200
    assert resp.json()["pin_set"] is True

    # Login with the new PIN should succeed
    login = await async_client.post(
        "/api/auth/login",
        json={"profile_id": str(sample_profile.id), "pin": new_pin},
    )
    assert login.status_code == 200, login.text

    # Login with a wrong PIN should fail (proves the new value really took)
    bad = await async_client.post(
        "/api/auth/login",
        json={"profile_id": str(sample_profile.id), "pin": "0000"},
    )
    assert bad.status_code == 401


async def test_update_profile_empty_pin_clears_it(
    authed_client: AsyncClient, sample_profile: Profile, db_session
) -> None:
    resp = await authed_client.put(
        f"/api/profiles/{sample_profile.id}",
        json={"pin": ""},
    )
    assert resp.status_code == 200
    assert resp.json()["pin_set"] is False


async def test_update_profile_invalid_pin_rejected(
    authed_client: AsyncClient, sample_profile: Profile
) -> None:
    resp = await authed_client.put(
        f"/api/profiles/{sample_profile.id}",
        json={"pin": "12"},
    )
    assert resp.status_code == 422


async def test_delete_profile(
    authed_client: AsyncClient, sample_household: Household
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
    get_resp = await authed_client.get(f"/api/profiles/{profile_id}")
    assert get_resp.status_code == 404


async def test_get_nonexistent_profile(authed_client: AsyncClient) -> None:
    fake_id = uuid.uuid4()
    resp = await authed_client.get(f"/api/profiles/{fake_id}")
    assert resp.status_code == 404
