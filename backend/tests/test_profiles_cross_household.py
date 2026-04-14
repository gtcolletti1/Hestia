"""Cross-household tests for profiles and auth (PIN) endpoints."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models.user import Household, Profile

pytestmark = pytest.mark.asyncio


# ── Profile cross-household tests ────────────────────────────────────────────


async def test_cross_household_update_profile(
    second_authed_client: AsyncClient,
    sample_profile: Profile,
) -> None:
    """User from household B cannot update a profile in household A."""
    resp = await second_authed_client.put(
        f"/api/profiles/{sample_profile.id}",
        json={"name": "Tampered Name"},
    )
    assert resp.status_code == 403


async def test_cross_household_delete_profile(
    second_authed_client: AsyncClient,
    sample_profile: Profile,
) -> None:
    """User from household B cannot delete a profile in household A."""
    resp = await second_authed_client.delete(f"/api/profiles/{sample_profile.id}")
    assert resp.status_code == 403


# ── PIN cross-household tests ────────────────────────────────────────────────


async def test_cross_household_set_pin(
    second_authed_client: AsyncClient,
    sample_profile: Profile,
) -> None:
    """Admin from household B cannot set PIN for a profile in household A."""
    resp = await second_authed_client.post(
        "/api/auth/pin",
        json={"profile_id": str(sample_profile.id), "pin": "9999"},
    )
    assert resp.status_code == 403


async def test_set_pin_own_profile(
    authed_client: AsyncClient,
    sample_profile: Profile,
) -> None:
    """User can set their own PIN."""
    resp = await authed_client.post(
        "/api/auth/pin",
        json={"profile_id": str(sample_profile.id), "pin": "4321"},
    )
    assert resp.status_code == 204


async def test_set_pin_nonexistent_profile(
    authed_client: AsyncClient,
) -> None:
    """Setting PIN for non-existent profile returns 404."""
    import uuid
    resp = await authed_client.post(
        "/api/auth/pin",
        json={"profile_id": str(uuid.uuid4()), "pin": "0000"},
    )
    assert resp.status_code == 404
