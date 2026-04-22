"""Tests for Admin / Household settings API."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Household, Profile, ProfileRole
from tests.conftest import _create_test_token

pytestmark = pytest.mark.asyncio


# ── Tests ────────────────────────────────────────────────────────────────────


async def test_get_default_settings(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    resp = await authed_client.get(
        "/api/admin/settings",
        params={"household_id": str(sample_household.id)},
    )
    assert resp.status_code == 200
    body = resp.json()

    assert body["name"] == sample_household.name
    assert body["theme"] == "light"
    assert body["privacy_mode"] is False
    assert body["time_format"] == "12h"
    assert body["modules_enabled"]["calendar"] is True
    assert body["modules_enabled"]["routines"] is True
    assert body["modules_enabled"]["lists"] is True
    assert body["modules_enabled"]["meals"] is True


async def test_update_settings_name(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    resp = await authed_client.put(
        "/api/admin/settings",
        params={"household_id": str(sample_household.id)},
        json={"name": "The Smiths"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "The Smiths"


async def test_update_settings_theme(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    resp = await authed_client.put(
        "/api/admin/settings",
        params={"household_id": str(sample_household.id)},
        json={"theme": "dark"},
    )
    assert resp.status_code == 200
    assert resp.json()["theme"] == "dark"


async def test_update_settings_time_format(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    resp = await authed_client.put(
        "/api/admin/settings",
        params={"household_id": str(sample_household.id)},
        json={"time_format": "24h"},
    )
    assert resp.status_code == 200
    assert resp.json()["time_format"] == "24h"


async def test_update_settings_time_format_invalid_rejected(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    resp = await authed_client.put(
        "/api/admin/settings",
        params={"household_id": str(sample_household.id)},
        json={"time_format": "13h"},
    )
    assert resp.status_code == 422


async def test_toggle_module(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    resp = await authed_client.patch(
        "/api/admin/modules",
        params={"household_id": str(sample_household.id)},
        json={"module": "meals", "enabled": False},
    )
    assert resp.status_code == 200
    assert resp.json()["modules_enabled"]["meals"] is False


async def test_toggle_invalid_module(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    resp = await authed_client.patch(
        "/api/admin/modules",
        params={"household_id": str(sample_household.id)},
        json={"module": "foobar", "enabled": True},
    )
    assert resp.status_code == 422


async def test_admin_requires_auth(
    async_client: AsyncClient, sample_household: Household
) -> None:
    resp = await async_client.get(
        "/api/admin/settings",
        params={"household_id": str(sample_household.id)},
    )
    assert resp.status_code in (401, 403)


async def test_admin_requires_admin_role(
    async_client: AsyncClient,
    db_session: AsyncSession,
    sample_household: Household,
) -> None:
    # Create a kid profile
    kid = Profile(
        household_id=sample_household.id,
        name="Kid User",
        color="#00FF00",
        role=ProfileRole.kid,
        is_active=True,
    )
    db_session.add(kid)
    await db_session.flush()
    await db_session.refresh(kid)

    kid_token = _create_test_token(kid.id, role="kid")
    kid_headers = {"Authorization": f"Bearer {kid_token}"}

    resp = await async_client.put(
        "/api/admin/settings",
        params={"household_id": str(sample_household.id)},
        json={"name": "Hacked Name"},
        headers=kid_headers,
    )
    assert resp.status_code == 403
