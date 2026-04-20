"""Tests for the points system — awarding, idempotency, ledger, balance.

PRD refs: US-2.3.2 (step completion awards points), US-2.4.1 (ledger).
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.models.user import Household, Profile

pytestmark = pytest.mark.asyncio


# ── Helpers ──────────────────────────────────────────────────────────────────


def _routine_with_points(household_id: uuid.UUID, profile_id: uuid.UUID) -> dict:
    return {
        "household_id": str(household_id),
        "profile_id": str(profile_id),
        "name": "Points Routine",
        "time_block": "morning",
        "days_of_week": [0, 1, 2, 3, 4, 5, 6],
        "steps": [
            {"label": "Step A", "icon": "🅰️", "sort_order": 0, "points_value": 5},
            {"label": "Step B", "icon": "🅱️", "sort_order": 1, "points_value": 10},
            {"label": "Step C (free)", "icon": "🆓", "sort_order": 2, "points_value": 0},
        ],
    }


async def _get_balance(client: AsyncClient, household_id: str, profile_id: str) -> int:
    resp = await client.get(
        "/api/rewards/points",
        params={"profile_id": profile_id, "household_id": household_id},
    )
    assert resp.status_code == 200
    return resp.json()["total_points"]


# ── Tests ────────────────────────────────────────────────────────────────────


async def test_completing_step_awards_points(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """Completing a step with points_value > 0 credits points immediately."""
    hid = str(sample_household.id)
    pid = str(sample_profile.id)

    # Baseline balance
    assert await _get_balance(authed_client, hid, pid) == 0

    # Create routine with point-valued steps
    r = await authed_client.post(
        "/api/routines", json=_routine_with_points(sample_household.id, sample_profile.id)
    )
    assert r.status_code == 201
    routine = r.json()
    step_a_id = routine["steps"][0]["id"]  # 5 points

    # Complete Step A
    resp = await authed_client.post(
        f"/api/routines/{routine['id']}/steps/{step_a_id}/complete",
        params={"profile_id": pid},
    )
    assert resp.status_code == 200

    # Balance should now be 5
    assert await _get_balance(authed_client, hid, pid) == 5


async def test_points_idempotent_per_step_per_day(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """Completing the same step twice on the same day does NOT double-award."""
    hid = str(sample_household.id)
    pid = str(sample_profile.id)

    r = await authed_client.post(
        "/api/routines", json=_routine_with_points(sample_household.id, sample_profile.id)
    )
    routine = r.json()
    step_a_id = routine["steps"][0]["id"]  # 5 pts

    # Complete twice
    await authed_client.post(
        f"/api/routines/{routine['id']}/steps/{step_a_id}/complete",
        params={"profile_id": pid},
    )
    await authed_client.post(
        f"/api/routines/{routine['id']}/steps/{step_a_id}/complete",
        params={"profile_id": pid},
    )

    # Should still be 5, not 10
    assert await _get_balance(authed_client, hid, pid) == 5


async def test_zero_point_step_no_award(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """A step with points_value=0 does not change the balance."""
    hid = str(sample_household.id)
    pid = str(sample_profile.id)

    r = await authed_client.post(
        "/api/routines", json=_routine_with_points(sample_household.id, sample_profile.id)
    )
    routine = r.json()
    free_step_id = routine["steps"][2]["id"]  # 0 points

    await authed_client.post(
        f"/api/routines/{routine['id']}/steps/{free_step_id}/complete",
        params={"profile_id": pid},
    )

    assert await _get_balance(authed_client, hid, pid) == 0


async def test_multiple_steps_accumulate_points(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """Points from different steps add up: 5 + 10 = 15."""
    hid = str(sample_household.id)
    pid = str(sample_profile.id)

    r = await authed_client.post(
        "/api/routines", json=_routine_with_points(sample_household.id, sample_profile.id)
    )
    routine = r.json()
    step_a = routine["steps"][0]["id"]  # 5
    step_b = routine["steps"][1]["id"]  # 10

    await authed_client.post(
        f"/api/routines/{routine['id']}/steps/{step_a}/complete",
        params={"profile_id": pid},
    )
    await authed_client.post(
        f"/api/routines/{routine['id']}/steps/{step_b}/complete",
        params={"profile_id": pid},
    )

    assert await _get_balance(authed_client, hid, pid) == 15


async def test_points_leaderboard_reflects_earned_points(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """Leaderboard shows the profile with their earned points total."""
    hid = str(sample_household.id)
    pid = str(sample_profile.id)

    r = await authed_client.post(
        "/api/routines", json=_routine_with_points(sample_household.id, sample_profile.id)
    )
    routine = r.json()
    step_a = routine["steps"][0]["id"]

    await authed_client.post(
        f"/api/routines/{routine['id']}/steps/{step_a}/complete",
        params={"profile_id": pid},
    )

    resp = await authed_client.get(
        "/api/rewards/leaderboard", params={"household_id": hid}
    )
    assert resp.status_code == 200
    entries = resp.json()
    matched = [e for e in entries if e["profile_id"] == pid]
    assert len(matched) == 1
    assert matched[0]["total_points"] == 5
