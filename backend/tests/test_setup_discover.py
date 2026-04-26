"""Tests for the unauthenticated bootstrap/discovery endpoint and
single-household appliance constraints introduced alongside it.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Household

pytestmark = pytest.mark.asyncio


# ── /api/setup/discover ──────────────────────────────────────────────────────


async def test_discover_when_empty(async_client: AsyncClient) -> None:
    """Fresh install: no households → setup_required=True, empty list."""
    resp = await async_client.get("/api/setup/discover")
    assert resp.status_code == 200
    body = resp.json()
    assert body["setup_required"] is True
    assert body["households"] == []


async def test_discover_when_one_household_exists(
    async_client: AsyncClient, sample_household: Household
) -> None:
    resp = await async_client.get("/api/setup/discover")
    assert resp.status_code == 200
    body = resp.json()
    assert body["setup_required"] is False
    assert len(body["households"]) == 1
    summary = body["households"][0]
    assert summary["id"] == str(sample_household.id)
    assert summary["name"] == sample_household.name
    # Minimal payload — no profiles, settings, timestamps, etc.
    assert set(summary.keys()) == {"id", "name"}


async def test_discover_is_unauthenticated(
    async_client: AsyncClient, sample_household: Household
) -> None:
    """The whole point of /setup/discover is that it works pre-login."""
    # No Authorization header at all.
    assert "Authorization" not in async_client.headers
    resp = await async_client.get("/api/setup/discover")
    assert resp.status_code == 200


# ── Single-household appliance: second POST blocked ──────────────────────────


async def test_create_second_household_blocked(
    async_client: AsyncClient, sample_household: Household
) -> None:
    """Once any household exists, POST /api/households returns 409."""
    resp = await async_client.post("/api/households", json={"name": "Another Family"})
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"].lower()


async def test_create_second_household_blocked_even_for_admin(
    authed_client: AsyncClient,
) -> None:
    """Authed admins also can't create a second household — appliance model."""
    resp = await authed_client.post("/api/households", json={"name": "Another Family"})
    assert resp.status_code == 409


# ── PIN-on-create (bootstrap path now works end-to-end) ──────────────────────


async def test_bootstrap_admin_with_pin_can_login(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """A fresh-install admin created via the wizard with a PIN can log in."""
    h_resp = await async_client.post("/api/households", json={"name": "Wizard Test"})
    assert h_resp.status_code == 201
    household_id = h_resp.json()["id"]

    p_resp = await async_client.post(
        "/api/profiles",
        json={
            "name": "Wizard Admin",
            "color": "#112233",
            "role": "admin",
            "household_id": household_id,
            "pin": "4242",
        },
    )
    assert p_resp.status_code == 201
    profile = p_resp.json()
    assert profile["pin_set"] is True

    login = await async_client.post(
        "/api/auth/login",
        json={"profile_id": profile["id"], "pin": "4242"},
    )
    assert login.status_code == 200
    assert "access_token" in login.json()


async def test_bootstrap_admin_without_pin_is_locked_out(
    async_client: AsyncClient,
) -> None:
    """Bootstrap admin created with no PIN can be created (allowed for now,
    but cannot then log in — proving why the wizard must collect a PIN)."""
    h_resp = await async_client.post("/api/households", json={"name": "Pinless"})
    household_id = h_resp.json()["id"]

    p_resp = await async_client.post(
        "/api/profiles",
        json={
            "name": "Pinless Admin",
            "color": "#445566",
            "role": "admin",
            "household_id": household_id,
        },
    )
    assert p_resp.status_code == 201
    assert p_resp.json()["pin_set"] is False

    login = await async_client.post(
        "/api/auth/login",
        json={"profile_id": p_resp.json()["id"], "pin": ""},
    )
    assert login.status_code == 423


async def test_pin_validation_rejects_short_or_non_digits(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    h_resp = await async_client.post("/api/households", json={"name": "PIN Validate"})
    household_id = h_resp.json()["id"]

    for bad_pin in ("123", "abcd", "12 34", "1" * 13):
        resp = await async_client.post(
            "/api/profiles",
            json={
                "name": "X",
                "color": "#000000",
                "role": "admin",
                "household_id": household_id,
                "pin": bad_pin,
            },
        )
        assert resp.status_code == 422, f"PIN {bad_pin!r} should be rejected"


async def test_get_household_requires_auth(
    async_client: AsyncClient, sample_household: Household
) -> None:
    resp = await async_client.get(f"/api/households/{sample_household.id}")
    assert resp.status_code == 401
