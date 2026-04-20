"""Tests for routine validation — empty steps rejected, days_of_week filtering.

PRD refs: US-2.3.1 (at least one step), US-2.3.4 (edit/delete).
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.models.user import Household, Profile

pytestmark = pytest.mark.asyncio


# ── Tests ────────────────────────────────────────────────────────────────────


async def test_create_routine_with_empty_steps_rejected(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """PRD: API rejects routines with empty steps[]."""
    resp = await authed_client.post(
        "/api/routines",
        json={
            "household_id": str(sample_household.id),
            "profile_id": str(sample_profile.id),
            "name": "Empty Routine",
            "time_block": "morning",
            "days_of_week": [0, 1, 2, 3, 4],
            "steps": [],
        },
    )
    assert resp.status_code == 422


async def test_create_routine_without_steps_field_rejected(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """Omitting the steps field entirely should be rejected (Field required or min_length)."""
    resp = await authed_client.post(
        "/api/routines",
        json={
            "household_id": str(sample_household.id),
            "name": "No Steps Field",
            "time_block": "evening",
            "days_of_week": [5, 6],
        },
    )
    # 422 because steps is required with min_length=1
    assert resp.status_code == 422


async def test_update_routine_name(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """Editing a routine's name works."""
    r = await authed_client.post(
        "/api/routines",
        json={
            "household_id": str(sample_household.id),
            "name": "Original Name",
            "time_block": "morning",
            "days_of_week": [0, 1, 2, 3, 4],
            "steps": [{"label": "Do thing", "sort_order": 0}],
        },
    )
    assert r.status_code == 201
    routine_id = r.json()["id"]

    resp = await authed_client.put(
        f"/api/routines/{routine_id}",
        json={"name": "Updated Name"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"


async def test_delete_routine(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """Deleting a routine returns 204 and it's gone."""
    r = await authed_client.post(
        "/api/routines",
        json={
            "household_id": str(sample_household.id),
            "name": "Delete Me",
            "time_block": "bedtime",
            "days_of_week": [0],
            "steps": [{"label": "Sleep", "sort_order": 0}],
        },
    )
    routine_id = r.json()["id"]

    resp = await authed_client.delete(f"/api/routines/{routine_id}")
    assert resp.status_code == 204

    resp = await authed_client.get(
        f"/api/routines/{routine_id}",
        params={"household_id": str(sample_household.id)},
    )
    assert resp.status_code == 404


async def test_delete_nonexistent_routine_404(
    authed_client: AsyncClient,
) -> None:
    fake_id = str(uuid.uuid4())
    resp = await authed_client.delete(f"/api/routines/{fake_id}")
    assert resp.status_code == 404


async def test_routine_active_toggle(
    authed_client: AsyncClient,
    sample_household: Household,
) -> None:
    """Setting is_active=False hides it from the active endpoint."""
    r = await authed_client.post(
        "/api/routines",
        json={
            "household_id": str(sample_household.id),
            "name": "Toggle Test",
            "time_block": "afternoon",
            "days_of_week": [0, 1, 2, 3, 4, 5, 6],
            "steps": [{"label": "Do it", "sort_order": 0}],
        },
    )
    routine_id = r.json()["id"]

    # Deactivate
    await authed_client.put(f"/api/routines/{routine_id}", json={"is_active": False})

    # Active endpoint should not include it
    resp = await authed_client.get(
        "/api/routines/active",
        params={"household_id": str(sample_household.id)},
    )
    assert resp.status_code == 200
    ids = [r["id"] for r in resp.json()]
    assert routine_id not in ids
