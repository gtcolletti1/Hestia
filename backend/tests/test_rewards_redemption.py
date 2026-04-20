"""Tests for rewards redemption — sufficient/insufficient points, inactive rewards, ledger.

PRD refs: US-2.4.2 (redeem if balance ≥ cost), US-2.4.3 (leaderboard).
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.models.user import Household, Profile

pytestmark = pytest.mark.asyncio


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _earn_points(
    client: AsyncClient,
    household_id: str,
    profile_id: str,
    target: int,
) -> None:
    """Create a routine and complete steps to earn exactly `target` points."""
    r = await client.post(
        "/api/routines",
        json={
            "household_id": household_id,
            "profile_id": profile_id,
            "name": f"Earn {target} pts",
            "time_block": "morning",
            "days_of_week": [0, 1, 2, 3, 4, 5, 6],
            "steps": [
                {"label": "Do it", "sort_order": 0, "points_value": target},
            ],
        },
    )
    routine = r.json()
    await client.post(
        f"/api/routines/{routine['id']}/steps/{routine['steps'][0]['id']}/complete",
        params={"profile_id": profile_id},
    )


async def _create_reward(
    client: AsyncClient, household_id: str, title: str, cost: int
) -> str:
    resp = await client.post(
        "/api/rewards",
        json={
            "title": title,
            "points_cost": cost,
            "household_id": household_id,
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# ── Tests ────────────────────────────────────────────────────────────────────


async def test_redeem_with_sufficient_points(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """A profile with enough points can redeem a reward; balance decreases."""
    hid = str(sample_household.id)
    pid = str(sample_profile.id)

    await _earn_points(authed_client, hid, pid, 100)
    reward_id = await _create_reward(authed_client, hid, "Ice cream", 50)

    resp = await authed_client.post(
        "/api/rewards/redeem",
        json={"reward_id": reward_id, "profile_id": pid, "household_id": hid},
    )
    assert resp.status_code == 200
    assert resp.json()["points"] == -50  # negative ledger entry

    # Balance should be 100 - 50 = 50
    balance_resp = await authed_client.get(
        "/api/rewards/points", params={"profile_id": pid, "household_id": hid}
    )
    assert balance_resp.json()["total_points"] == 50


async def test_redeem_exact_balance(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """Redeeming a reward that costs exactly the balance succeeds."""
    hid = str(sample_household.id)
    pid = str(sample_profile.id)

    await _earn_points(authed_client, hid, pid, 30)
    reward_id = await _create_reward(authed_client, hid, "Exact match", 30)

    resp = await authed_client.post(
        "/api/rewards/redeem",
        json={"reward_id": reward_id, "profile_id": pid, "household_id": hid},
    )
    assert resp.status_code == 200

    balance_resp = await authed_client.get(
        "/api/rewards/points", params={"profile_id": pid, "household_id": hid}
    )
    assert balance_resp.json()["total_points"] == 0


async def test_redeem_insufficient_points_rejected(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """49 points cannot redeem a 50-point reward."""
    hid = str(sample_household.id)
    pid = str(sample_profile.id)

    await _earn_points(authed_client, hid, pid, 49)
    reward_id = await _create_reward(authed_client, hid, "Too expensive", 50)

    resp = await authed_client.post(
        "/api/rewards/redeem",
        json={"reward_id": reward_id, "profile_id": pid, "household_id": hid},
    )
    assert resp.status_code == 400
    assert "not enough points" in resp.json()["detail"].lower()


async def test_redeem_nonexistent_reward_404(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    hid = str(sample_household.id)
    pid = str(sample_profile.id)

    resp = await authed_client.post(
        "/api/rewards/redeem",
        json={
            "reward_id": str(uuid.uuid4()),
            "profile_id": pid,
            "household_id": hid,
        },
    )
    assert resp.status_code == 404


async def test_redeem_creates_negative_ledger_entry(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """Redemption creates a ledger entry with negative points and the reward_id."""
    hid = str(sample_household.id)
    pid = str(sample_profile.id)

    await _earn_points(authed_client, hid, pid, 25)
    reward_id = await _create_reward(authed_client, hid, "Sticker pack", 10)

    resp = await authed_client.post(
        "/api/rewards/redeem",
        json={"reward_id": reward_id, "profile_id": pid, "household_id": hid},
    )
    body = resp.json()
    assert body["points"] < 0
    assert "redeem" in body["reason"].lower() or "sticker" in body["reason"].lower()


async def test_inactive_reward_excluded_from_list(
    authed_client: AsyncClient,
    sample_household: Household,
) -> None:
    """Deactivated rewards do not appear in GET /api/rewards."""
    hid = str(sample_household.id)
    reward_id = await _create_reward(authed_client, hid, "Deactivate me", 5)

    # Deactivate
    await authed_client.put(f"/api/rewards/{reward_id}", json={"is_active": False})

    resp = await authed_client.get("/api/rewards", params={"household_id": hid})
    ids = [r["id"] for r in resp.json()]
    assert reward_id not in ids
