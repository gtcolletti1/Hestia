"""Tests for the weather API endpoint."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Household, Profile


# ── Unauthenticated access ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_weather_requires_auth(async_client: AsyncClient, sample_household: Household):
    resp = await async_client.get("/api/weather", params={"household_id": str(sample_household.id)})
    assert resp.status_code == 401


# ── No location configured ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_weather_no_location(authed_client: AsyncClient, sample_household: Household):
    resp = await authed_client.get("/api/weather", params={"household_id": str(sample_household.id)})
    assert resp.status_code == 422
    assert "location not configured" in resp.json()["detail"].lower()


# ── Cross-household access denied ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_weather_cross_household_denied(
    authed_client: AsyncClient,
    second_household: Household,
    second_profile: Profile,
):
    resp = await authed_client.get(
        "/api/weather", params={"household_id": str(second_household.id)}
    )
    assert resp.status_code == 403


# ── Weather module toggle ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_weather_module_toggle(authed_client: AsyncClient, sample_household: Household):
    """Weather module can be toggled on/off via admin modules endpoint."""
    hid = str(sample_household.id)

    # Toggle weather off
    resp = await authed_client.patch(
        "/api/admin/modules",
        params={"household_id": hid},
        json={"module": "weather", "enabled": False},
    )
    assert resp.status_code == 200
    assert resp.json()["modules_enabled"]["weather"] is False

    # Toggle weather back on
    resp = await authed_client.patch(
        "/api/admin/modules",
        params={"household_id": hid},
        json={"module": "weather", "enabled": True},
    )
    assert resp.status_code == 200
    assert resp.json()["modules_enabled"]["weather"] is True


# ── Weather location settings ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_weather_location_settings(authed_client: AsyncClient, sample_household: Household):
    """Weather lat/lon/units can be saved and retrieved via admin settings."""
    hid = str(sample_household.id)

    # Set weather location
    resp = await authed_client.put(
        "/api/admin/settings",
        params={"household_id": hid},
        json={"weather_lat": 40.7128, "weather_lon": -74.006, "weather_units": "imperial"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["weather_lat"] == 40.7128
    assert data["weather_lon"] == -74.006
    assert data["weather_units"] == "imperial"

    # Verify settings persist on GET
    resp = await authed_client.get("/api/admin/settings", params={"household_id": hid})
    assert resp.status_code == 200
    data = resp.json()
    assert data["weather_lat"] == 40.7128
    assert data["weather_lon"] == -74.006
    assert data["weather_units"] == "imperial"


@pytest.mark.asyncio
async def test_weather_metric_units(authed_client: AsyncClient, sample_household: Household):
    """Weather units can be set to metric."""
    hid = str(sample_household.id)
    resp = await authed_client.put(
        "/api/admin/settings",
        params={"household_id": hid},
        json={"weather_units": "metric"},
    )
    assert resp.status_code == 200
    assert resp.json()["weather_units"] == "metric"


# ── Weather endpoint with location but no API key ────────────────────────────


@pytest.mark.asyncio
async def test_weather_no_api_key(
    authed_client: AsyncClient,
    sample_household: Household,
    db_session: AsyncSession,
):
    """Weather endpoint returns 503 when API key is not configured."""
    hid = str(sample_household.id)

    # First set a location
    await authed_client.put(
        "/api/admin/settings",
        params={"household_id": hid},
        json={"weather_lat": 40.7128, "weather_lon": -74.006},
    )

    # Now try to get weather (test env has no API key)
    resp = await authed_client.get("/api/weather", params={"household_id": hid})
    assert resp.status_code == 503
    assert "api key" in resp.json()["detail"].lower()
