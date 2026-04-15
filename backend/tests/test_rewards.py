"""Tests for the rewards system API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Household, Profile


# ── Unauthenticated access ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rewards_list_requires_auth(async_client: AsyncClient, sample_household: Household):
    resp = await async_client.get("/api/rewards", params={"household_id": str(sample_household.id)})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_leaderboard_requires_auth(async_client: AsyncClient, sample_household: Household):
    resp = await async_client.get("/api/rewards/leaderboard", params={"household_id": str(sample_household.id)})
    assert resp.status_code == 401


# ── Rewards CRUD ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_reward(authed_client: AsyncClient, sample_household: Household):
    resp = await authed_client.post("/api/rewards", json={
        "title": "Extra screen time",
        "description": "30 minutes of extra screen time",
        "points_cost": 50,
        "icon": "📱",
        "household_id": str(sample_household.id),
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Extra screen time"
    assert data["points_cost"] == 50
    assert data["icon"] == "📱"


@pytest.mark.asyncio
async def test_list_rewards(authed_client: AsyncClient, sample_household: Household):
    await authed_client.post("/api/rewards", json={
        "title": "Reward A",
        "points_cost": 20,
        "household_id": str(sample_household.id),
    })
    await authed_client.post("/api/rewards", json={
        "title": "Reward B",
        "points_cost": 10,
        "household_id": str(sample_household.id),
    })

    resp = await authed_client.get("/api/rewards", params={"household_id": str(sample_household.id)})
    assert resp.status_code == 200
    rewards = resp.json()
    assert len(rewards) == 2
    # Sorted by points_cost
    assert rewards[0]["points_cost"] <= rewards[1]["points_cost"]


@pytest.mark.asyncio
async def test_update_reward(authed_client: AsyncClient, sample_household: Household):
    resp = await authed_client.post("/api/rewards", json={
        "title": "Original",
        "points_cost": 10,
        "household_id": str(sample_household.id),
    })
    reward_id = resp.json()["id"]

    resp = await authed_client.put(f"/api/rewards/{reward_id}", json={
        "title": "Updated",
        "points_cost": 25,
    })
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated"
    assert resp.json()["points_cost"] == 25


@pytest.mark.asyncio
async def test_delete_reward(authed_client: AsyncClient, sample_household: Household):
    resp = await authed_client.post("/api/rewards", json={
        "title": "Delete me",
        "points_cost": 5,
        "household_id": str(sample_household.id),
    })
    reward_id = resp.json()["id"]

    resp = await authed_client.delete(f"/api/rewards/{reward_id}")
    assert resp.status_code == 204


# ── Points & Leaderboard ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_point_balance_starts_zero(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
):
    resp = await authed_client.get("/api/rewards/points", params={
        "profile_id": str(sample_profile.id),
        "household_id": str(sample_household.id),
    })
    assert resp.status_code == 200
    assert resp.json()["total_points"] == 0


@pytest.mark.asyncio
async def test_leaderboard_returns_profiles(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
):
    resp = await authed_client.get("/api/rewards/leaderboard", params={
        "household_id": str(sample_household.id),
    })
    assert resp.status_code == 200
    entries = resp.json()
    assert len(entries) >= 1
    assert any(e["profile_id"] == str(sample_profile.id) for e in entries)


# ── Redeem ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_redeem_insufficient_points(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
):
    # Create a reward
    resp = await authed_client.post("/api/rewards", json={
        "title": "Expensive",
        "points_cost": 1000,
        "household_id": str(sample_household.id),
    })
    reward_id = resp.json()["id"]

    # Try to redeem with 0 points
    resp = await authed_client.post("/api/rewards/redeem", json={
        "reward_id": reward_id,
        "profile_id": str(sample_profile.id),
        "household_id": str(sample_household.id),
    })
    assert resp.status_code == 400
    assert "not enough points" in resp.json()["detail"].lower()


# ── Cross-household isolation ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rewards_cross_household_denied(
    authed_client: AsyncClient,
    second_household: Household,
    second_profile: Profile,
):
    resp = await authed_client.get("/api/rewards", params={
        "household_id": str(second_household.id),
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_rewards_cross_household_create_denied(
    authed_client: AsyncClient,
    second_household: Household,
    second_profile: Profile,
):
    resp = await authed_client.post("/api/rewards", json={
        "title": "Sneaky",
        "points_cost": 10,
        "household_id": str(second_household.id),
    })
    assert resp.status_code == 403


# ── 404 handling ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_nonexistent_reward(authed_client: AsyncClient):
    resp = await authed_client.put(
        "/api/rewards/00000000-0000-0000-0000-000000000000",
        json={"title": "nope"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_reward(authed_client: AsyncClient):
    resp = await authed_client.delete("/api/rewards/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
