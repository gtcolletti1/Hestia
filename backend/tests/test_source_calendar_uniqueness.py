"""Source calendar uniqueness — prevent silent double-connections.

Closes the third root cause of dashboard / splash agenda duplicates: a
user accidentally connecting the same external calendar twice (e.g.,
"primary" and the explicit calendar id) used to create two
SourceCalendar rows, each pulling its own copy of every event into the
database.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_duplicate_external_calendar_rejected(
    authed_client: AsyncClient, sample_household
):
    payload = {
        "name": "Family Google",
        "provider": "google",
        "household_id": str(sample_household.id),
        "external_id": "primary",
    }
    first = await authed_client.post("/api/calendars", json=payload)
    assert first.status_code == 201

    dup = await authed_client.post("/api/calendars", json={**payload, "name": "Dup"})
    assert dup.status_code == 409
    assert "already connected" in dup.json()["detail"].lower()


async def test_local_calendars_can_share_null_external_id(
    authed_client: AsyncClient, sample_household
):
    payload = {
        "name": "Manual A",
        "provider": "local",
        "household_id": str(sample_household.id),
    }
    a = await authed_client.post("/api/calendars", json=payload)
    b = await authed_client.post(
        "/api/calendars", json={**payload, "name": "Manual B"}
    )
    assert a.status_code == 201
    assert b.status_code == 201


async def test_different_external_ids_allowed(
    authed_client: AsyncClient, sample_household
):
    base = {
        "provider": "google",
        "household_id": str(sample_household.id),
    }
    one = await authed_client.post(
        "/api/calendars", json={**base, "name": "Primary", "external_id": "primary"}
    )
    two = await authed_client.post(
        "/api/calendars",
        json={**base, "name": "Work", "external_id": "work@group.calendar.google.com"},
    )
    assert one.status_code == 201
    assert two.status_code == 201
