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


# ── Uncomplete / no-double-award (Bug 1 regression) ─────────────────────────


async def _balance(client: AsyncClient, household_id, profile_id) -> int:
    """Helper: read current point balance via the rewards API."""
    r = await client.get(
        "/api/rewards/points",
        params={"household_id": str(household_id), "profile_id": str(profile_id)},
    )
    assert r.status_code == 200, r.text
    return r.json()["total_points"]


async def test_complete_step_is_idempotent_does_not_double_award(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """Calling complete twice for the same step awards points exactly once."""
    pid = str(sample_profile.id)
    r = await authed_client.post(
        "/api/routines",
        json=_routine_payload(sample_household.id, sample_profile.id),
    )
    routine = r.json()
    step = routine["steps"][0]  # points_value = 1

    base = await _balance(authed_client, sample_household.id, sample_profile.id)

    for _ in range(3):
        resp = await authed_client.post(
            f"/api/routines/{routine['id']}/steps/{step['id']}/complete",
            params={"profile_id": pid},
        )
        assert resp.status_code == 200
        assert resp.json()["completed_steps"].count(step["id"]) == 1

    assert await _balance(authed_client, sample_household.id, sample_profile.id) == base + 1


async def test_uncomplete_step_reverses_points_and_marks_not_full(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """Uncompleting a credited step debits the points and clears full flag."""
    pid = str(sample_profile.id)
    r = await authed_client.post(
        "/api/routines",
        json=_routine_payload(sample_household.id, sample_profile.id),
    )
    routine = r.json()
    steps = routine["steps"]

    base = await _balance(authed_client, sample_household.id, sample_profile.id)

    # Complete every step → fully completed, +3 points
    for s in steps:
        await authed_client.post(
            f"/api/routines/{routine['id']}/steps/{s['id']}/complete",
            params={"profile_id": pid},
        )
    assert await _balance(authed_client, sample_household.id, sample_profile.id) == base + 3

    # Uncomplete the middle step → -1 point, no longer fully completed
    resp = await authed_client.post(
        f"/api/routines/{routine['id']}/steps/{steps[1]['id']}/uncomplete",
        params={"profile_id": pid},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert steps[1]["id"] not in body["completed_steps"]
    assert body["is_fully_completed"] is False
    assert body["completed_at"] is None
    assert await _balance(authed_client, sample_household.id, sample_profile.id) == base + 2


async def test_uncomplete_then_recheck_does_not_double_award(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """The previously-reported bug: uncheck/recheck should not farm points."""
    pid = str(sample_profile.id)
    r = await authed_client.post(
        "/api/routines",
        json=_routine_payload(sample_household.id, sample_profile.id),
    )
    routine = r.json()
    step = routine["steps"][0]  # points_value = 1

    base = await _balance(authed_client, sample_household.id, sample_profile.id)

    # check, uncheck, check, uncheck, check  (5 toggles ending checked)
    for action in ("complete", "uncomplete", "complete", "uncomplete", "complete"):
        resp = await authed_client.post(
            f"/api/routines/{routine['id']}/steps/{step['id']}/{action}",
            params={"profile_id": pid},
        )
        assert resp.status_code == 200

    # Net balance change: exactly +1 (one credit currently held)
    assert await _balance(authed_client, sample_household.id, sample_profile.id) == base + 1


async def test_uncomplete_step_never_completed_is_noop(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """Uncompleting a step that was never completed today is a 200 no-op."""
    pid = str(sample_profile.id)
    r = await authed_client.post(
        "/api/routines",
        json=_routine_payload(sample_household.id, sample_profile.id),
    )
    routine = r.json()
    step = routine["steps"][0]

    base = await _balance(authed_client, sample_household.id, sample_profile.id)

    resp = await authed_client.post(
        f"/api/routines/{routine['id']}/steps/{step['id']}/uncomplete",
        params={"profile_id": pid},
    )
    assert resp.status_code == 200
    assert resp.json()["completed_steps"] == []
    assert await _balance(authed_client, sample_household.id, sample_profile.id) == base


async def test_uncomplete_zero_point_step_does_not_create_ledger_entry(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """Steps with points_value=0 should never produce ledger entries either way."""
    payload = _routine_payload(sample_household.id, sample_profile.id)
    payload["steps"][0]["points_value"] = 0
    pid = str(sample_profile.id)
    r = await authed_client.post("/api/routines", json=payload)
    routine = r.json()
    step = routine["steps"][0]

    base = await _balance(authed_client, sample_household.id, sample_profile.id)

    await authed_client.post(
        f"/api/routines/{routine['id']}/steps/{step['id']}/complete",
        params={"profile_id": pid},
    )
    await authed_client.post(
        f"/api/routines/{routine['id']}/steps/{step['id']}/uncomplete",
        params={"profile_id": pid},
    )

    assert await _balance(authed_client, sample_household.id, sample_profile.id) == base
