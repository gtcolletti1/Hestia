"""Tests for profile lifecycle — deactivation, onboarding, first admin.

PRD refs: US-2.9.1 (deactivation), US-2.9.2 (auth), US-2.9.3 (onboarding).
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Household, Profile, ProfileRole

pytestmark = pytest.mark.asyncio


# ── Tests ────────────────────────────────────────────────────────────────────


async def test_create_profile(
    authed_client: AsyncClient,
    sample_household: Household,
) -> None:
    """Creating a standard profile works."""
    resp = await authed_client.post(
        "/api/profiles",
        json={
            "household_id": str(sample_household.id),
            "name": "Child One",
            "color": "#22C55E",
            "role": "standard",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Child One"
    assert body["role"] == "standard"
    assert body["is_active"] is True


async def test_deactivate_profile(
    authed_client: AsyncClient,
    sample_household: Household,
) -> None:
    """Deactivating a profile hides it from the active list."""
    # Create a profile to deactivate
    r = await authed_client.post(
        "/api/profiles",
        json={
            "household_id": str(sample_household.id),
            "name": "Deactivate Me",
            "color": "#EF4444",
        },
    )
    profile_id = r.json()["id"]

    # Deactivate
    resp = await authed_client.put(
        f"/api/profiles/{profile_id}",
        json={"is_active": False},
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


async def test_deactivated_profile_cannot_login(
    async_client: AsyncClient,
    db_session: AsyncSession,
    sample_household: Household,
) -> None:
    """An inactive profile cannot log in."""
    profile = Profile(
        household_id=sample_household.id,
        name="Inactive User",
        color="#999999",
        role=ProfileRole.standard,
        is_active=False,
    )
    db_session.add(profile)
    await db_session.flush()
    await db_session.refresh(profile)

    resp = await async_client.post(
        "/api/auth/login",
        json={"profile_id": str(profile.id), "pin": ""},
    )
    # Should be rejected — inactive profiles cannot log in
    assert resp.status_code in (401, 403)


async def test_reactivate_profile(
    authed_client: AsyncClient,
    sample_household: Household,
) -> None:
    """A deactivated profile can be re-activated."""
    r = await authed_client.post(
        "/api/profiles",
        json={
            "household_id": str(sample_household.id),
            "name": "Toggle Active",
            "color": "#3B82F6",
        },
    )
    pid = r.json()["id"]

    # Deactivate then reactivate
    await authed_client.put(f"/api/profiles/{pid}", json={"is_active": False})
    resp = await authed_client.put(f"/api/profiles/{pid}", json={"is_active": True})
    assert resp.status_code == 200
    assert resp.json()["is_active"] is True


async def test_create_household(async_client: AsyncClient) -> None:
    """Creating a household returns the household with an ID."""
    resp = await async_client.post(
        "/api/households", json={"name": "New Family"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "New Family"
    assert "id" in body


async def test_profile_update_preserves_fields(
    authed_client: AsyncClient,
    sample_household: Household,
) -> None:
    """Updating one field doesn't clear others."""
    r = await authed_client.post(
        "/api/profiles",
        json={
            "household_id": str(sample_household.id),
            "name": "Partial Update",
            "color": "#F59E0B",
            "role": "standard",
        },
    )
    pid = r.json()["id"]

    # Update only name
    resp = await authed_client.put(
        f"/api/profiles/{pid}", json={"name": "New Name"}
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"
    assert resp.json()["color"] == "#F59E0B"  # preserved


async def test_delete_profile(
    authed_client: AsyncClient,
    sample_household: Household,
) -> None:
    """Deleting a profile returns 204."""
    r = await authed_client.post(
        "/api/profiles",
        json={
            "household_id": str(sample_household.id),
            "name": "Delete Me",
            "color": "#DC2626",
        },
    )
    pid = r.json()["id"]

    resp = await authed_client.delete(f"/api/profiles/{pid}")
    assert resp.status_code == 204
