"""Tests for routine completion tracking and the is_fully_completed flag.

PRD refs: US-2.3.2 (step tracking, full completion).
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.models.user import Household, Profile

pytestmark = pytest.mark.asyncio


# ── Helpers ──────────────────────────────────────────────────────────────────


def _routine_payload(household_id: uuid.UUID, profile_id: uuid.UUID) -> dict:
    return {
        "household_id": str(household_id),
        "profile_id": str(profile_id),
        "name": "Completion Tracking",
        "time_block": "morning",
        "days_of_week": [0, 1, 2, 3, 4, 5, 6],
        "steps": [
            {"label": "Step 1", "icon": "1️⃣", "sort_order": 0, "points_value": 1},
            {"label": "Step 2", "icon": "2️⃣", "sort_order": 1, "points_value": 1},
            {"label": "Step 3", "icon": "3️⃣", "sort_order": 2, "points_value": 1},
        ],
    }


# ── Tests ────────────────────────────────────────────────────────────────────


async def test_first_step_creates_completion_record(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """Completing the first step creates a RoutineCompletion record."""
    pid = str(sample_profile.id)
    r = await authed_client.post(
        "/api/routines", json=_routine_payload(sample_household.id, sample_profile.id)
    )
    routine = r.json()

    resp = await authed_client.post(
        f"/api/routines/{routine['id']}/steps/{routine['steps'][0]['id']}/complete",
        params={"profile_id": pid},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "id" in body
    assert body["routine_id"] == routine["id"]
    assert body["profile_id"] == pid
    assert body["date"] is not None


async def test_completed_steps_array_tracks_step_ids(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """completed_steps accumulates step IDs as they are completed."""
    pid = str(sample_profile.id)
    r = await authed_client.post(
        "/api/routines", json=_routine_payload(sample_household.id, sample_profile.id)
    )
    routine = r.json()
    steps = routine["steps"]

    # Complete step 1
    resp1 = await authed_client.post(
        f"/api/routines/{routine['id']}/steps/{steps[0]['id']}/complete",
        params={"profile_id": pid},
    )
    assert len(resp1.json()["completed_steps"]) == 1
    assert steps[0]["id"] in resp1.json()["completed_steps"]

    # Complete step 2
    resp2 = await authed_client.post(
        f"/api/routines/{routine['id']}/steps/{steps[1]['id']}/complete",
        params={"profile_id": pid},
    )
    cs = resp2.json()["completed_steps"]
    assert len(cs) == 2
    assert steps[0]["id"] in cs
    assert steps[1]["id"] in cs


async def test_fully_completed_when_all_steps_done(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """is_fully_completed is True only after all steps are marked."""
    pid = str(sample_profile.id)
    r = await authed_client.post(
        "/api/routines", json=_routine_payload(sample_household.id, sample_profile.id)
    )
    routine = r.json()
    steps = routine["steps"]

    # Complete first 2 — not fully done yet
    for s in steps[:2]:
        resp = await authed_client.post(
            f"/api/routines/{routine['id']}/steps/{s['id']}/complete",
            params={"profile_id": pid},
        )
    assert resp.json()["is_fully_completed"] is False

    # Complete the last step
    resp = await authed_client.post(
        f"/api/routines/{routine['id']}/steps/{steps[2]['id']}/complete",
        params={"profile_id": pid},
    )
    assert resp.json()["is_fully_completed"] is True
    assert resp.json()["completed_at"] is not None


async def test_partial_completion_not_fully_completed(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """A routine with only some steps done is NOT fully completed."""
    pid = str(sample_profile.id)
    r = await authed_client.post(
        "/api/routines", json=_routine_payload(sample_household.id, sample_profile.id)
    )
    routine = r.json()

    resp = await authed_client.post(
        f"/api/routines/{routine['id']}/steps/{routine['steps'][0]['id']}/complete",
        params={"profile_id": pid},
    )
    assert resp.json()["is_fully_completed"] is False
    assert resp.json()["completed_at"] is None


async def test_complete_nonexistent_step_returns_404(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """Completing a step that doesn't belong to the routine returns 404."""
    pid = str(sample_profile.id)
    r = await authed_client.post(
        "/api/routines", json=_routine_payload(sample_household.id, sample_profile.id)
    )
    routine = r.json()
    fake_step = str(uuid.uuid4())

    resp = await authed_client.post(
        f"/api/routines/{routine['id']}/steps/{fake_step}/complete",
        params={"profile_id": pid},
    )
    assert resp.status_code == 404
