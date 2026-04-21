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


async def test_duplicate_routine_copies_all_steps(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """Duplicating a routine creates a 'Copy of ...' with identical steps."""
    # Create original
    resp = await authed_client.post(
        "/api/routines",
        json={
            "household_id": str(sample_household.id),
            "name": "Bedtime",
            "time_block": "bedtime",
            "days_of_week": [0, 1, 2, 3, 4],
            "steps": [
                {"label": "Brush teeth", "icon": "🪥", "sort_order": 0, "points_value": 5},
                {"label": "Story time", "icon": "📖", "sort_order": 1, "points_value": 0},
                {"label": "Lights out", "icon": "💤", "sort_order": 2, "points_value": 0},
            ],
        },
    )
    assert resp.status_code == 201
    original = resp.json()

    # Duplicate
    resp = await authed_client.post(f"/api/routines/{original['id']}/duplicate")
    assert resp.status_code == 201
    copy = resp.json()

    assert copy["name"] == "Copy of Bedtime"
    assert copy["id"] != original["id"]
    assert copy["time_block"] == original["time_block"]
    assert copy["days_of_week"] == original["days_of_week"]
    assert copy["is_active"] == original["is_active"]
    assert len(copy["steps"]) == 3
    assert copy["steps"][0]["label"] == "Brush teeth"
    assert copy["steps"][0]["points_value"] == 5
    # Steps should have new IDs
    orig_step_ids = {s["id"] for s in original["steps"]}
    copy_step_ids = {s["id"] for s in copy["steps"]}
    assert orig_step_ids.isdisjoint(copy_step_ids)


async def test_duplicate_nonexistent_routine_404(
    authed_client: AsyncClient,
) -> None:
    """Duplicating a nonexistent routine returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await authed_client.post(f"/api/routines/{fake_id}/duplicate")
    assert resp.status_code == 404
