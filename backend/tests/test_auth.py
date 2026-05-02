"""Tests for the auth API (PIN login, JWT, /me)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Household, Profile

pytestmark = pytest.mark.asyncio


async def test_login_with_pin(
    async_client: AsyncClient,
    sample_profile: Profile,
) -> None:
    resp = await async_client.post(
        "/api/auth/login",
        json={"profile_id": str(sample_profile.id), "pin": "1234"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["profile"]["id"] == str(sample_profile.id)


async def test_login_wrong_pin(
    async_client: AsyncClient,
    sample_profile: Profile,
) -> None:
    resp = await async_client.post(
        "/api/auth/login",
        json={"profile_id": str(sample_profile.id), "pin": "9999"},
    )
    assert resp.status_code == 401


async def test_get_me(
    async_client: AsyncClient,
    sample_profile: Profile,
    auth_headers: dict[str, str],
) -> None:
    resp = await async_client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(sample_profile.id)
    assert body["name"] == sample_profile.name
    assert body["role"] == "admin"


async def test_unauthorized(async_client: AsyncClient) -> None:
    resp = await async_client.get("/api/auth/me")
    assert resp.status_code in (401, 403)


# ── /auth/verify-pin (used by the privacy-mode reveal gate) ─────────────────


async def test_verify_pin_accepts_own_pin(
    async_client: AsyncClient,
    sample_profile: Profile,
    auth_headers: dict[str, str],
) -> None:
    """The authenticated user's own PIN unlocks privacy reveal."""
    resp = await async_client.post(
        "/api/auth/verify-pin",
        json={"pin": "1234"},
        headers=auth_headers,
    )
    assert resp.status_code == 204


async def test_verify_pin_accepts_any_household_member_pin(
    async_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """Another member of the same household can unlock with their own PIN.

    The wall display is shared, so any household member who is willing to
    identify themselves with a PIN should be able to reveal details.
    """
    from passlib.context import CryptContext

    other = Profile(
        household_id=sample_household.id,
        name="Sibling",
        role=sample_profile.role,
        color="#22c55e",
        pin_hash=CryptContext(schemes=["bcrypt"]).hash("5555"),
    )
    db_session.add(other)
    await db_session.flush()

    resp = await async_client.post(
        "/api/auth/verify-pin",
        json={"pin": "5555"},
        headers=auth_headers,
    )
    assert resp.status_code == 204


async def test_verify_pin_rejects_wrong_pin(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    resp = await async_client.post(
        "/api/auth/verify-pin",
        json={"pin": "0000"},
        headers=auth_headers,
    )
    assert resp.status_code == 401


async def test_verify_pin_rejects_empty_pin(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    resp = await async_client.post(
        "/api/auth/verify-pin",
        json={"pin": ""},
        headers=auth_headers,
    )
    assert resp.status_code == 401


async def test_verify_pin_rejects_other_household_pin(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    second_profile: Profile,
) -> None:
    """A PIN that belongs to a profile in a *different* household must not
    unlock the current household."""
    resp = await async_client.post(
        "/api/auth/verify-pin",
        json={"pin": "5678"},  # second_profile's PIN
        headers=auth_headers,
    )
    assert resp.status_code == 401


async def test_verify_pin_requires_authentication(
    async_client: AsyncClient,
) -> None:
    resp = await async_client.post(
        "/api/auth/verify-pin",
        json={"pin": "1234"},
    )
    assert resp.status_code in (401, 403)
