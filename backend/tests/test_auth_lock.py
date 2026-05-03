"""Tests for the POST /api/auth/lock endpoint (PRD US-2.12.6, "Lock now")."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_lock_returns_204_for_authed_user(
    authed_client: AsyncClient,
) -> None:
    resp = await authed_client.post("/api/auth/lock")
    assert resp.status_code == 204
    assert resp.text == ""


async def test_lock_requires_authentication(
    async_client: AsyncClient,
) -> None:
    resp = await async_client.post("/api/auth/lock")
    assert resp.status_code == 401


async def test_lock_rejects_invalid_token(
    async_client: AsyncClient,
) -> None:
    async_client.headers["Authorization"] = "Bearer not-a-real-token"
    resp = await async_client.post("/api/auth/lock")
    assert resp.status_code == 401
