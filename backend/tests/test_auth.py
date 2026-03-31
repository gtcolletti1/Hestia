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
