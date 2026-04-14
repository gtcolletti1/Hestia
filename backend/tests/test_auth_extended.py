"""Extended auth tests (PIN-less login, inactive profiles, cross-household)."""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Household, Profile, ProfileRole

pytestmark = pytest.mark.asyncio


# ── Tests ────────────────────────────────────────────────────────────────────


async def test_login_without_pin(
    async_client: AsyncClient,
    db_session: AsyncSession,
    sample_household: Household,
) -> None:
    """A profile with no pin_hash can login with an empty pin."""
    profile = Profile(
        household_id=sample_household.id,
        name="No Pin User",
        color="#AABBCC",
        role=ProfileRole.standard,
        pin_hash=None,
        is_active=True,
    )
    db_session.add(profile)
    await db_session.flush()
    await db_session.refresh(profile)

    resp = await async_client.post(
        "/api/auth/login",
        json={"profile_id": str(profile.id), "pin": ""},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["profile"]["id"] == str(profile.id)


async def test_login_nonexistent_profile(async_client: AsyncClient) -> None:
    resp = await async_client.post(
        "/api/auth/login",
        json={"profile_id": str(uuid.uuid4()), "pin": ""},
    )
    assert resp.status_code == 401


async def test_login_inactive_profile(
    async_client: AsyncClient,
    db_session: AsyncSession,
    sample_household: Household,
) -> None:
    profile = Profile(
        household_id=sample_household.id,
        name="Inactive User",
        color="#112233",
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
    assert resp.status_code == 401


async def test_cross_household_dashboard(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """A user from household A cannot view the dashboard for household B."""
    # Create household A + profile
    household_a = Household(name="Family A")
    db_session.add(household_a)
    await db_session.flush()

    profile_a = Profile(
        household_id=household_a.id,
        name="User A",
        color="#000000",
        role=ProfileRole.admin,
        is_active=True,
    )
    db_session.add(profile_a)
    await db_session.flush()

    # Create household B
    household_b = Household(name="Family B")
    db_session.add(household_b)
    await db_session.flush()

    # Login as profile A
    login_resp = await async_client.post(
        "/api/auth/login",
        json={"profile_id": str(profile_a.id), "pin": ""},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Try dashboard for household B — should be 403
    resp = await async_client.get(
        "/api/dashboard",
        params={"household_id": str(household_b.id)},
        headers=headers,
    )
    assert resp.status_code == 403
