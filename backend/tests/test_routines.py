"""Tests for the routines API."""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.routine import Routine, RoutineStep, TimeBlock
from app.models.user import Household, Profile

pytestmark = pytest.mark.asyncio


# ── Helpers ──────────────────────────────────────────────────────────────────


def _routine_payload(household_id: uuid.UUID, profile_id: uuid.UUID | None = None) -> dict:
    base = {
        "household_id": str(household_id),
        "name": "Morning Routine",
        "time_block": "morning",
        "days_of_week": [0, 1, 2, 3, 4],
        "steps": [
            {"label": "Brush teeth", "icon": "🪥", "sort_order": 0},
            {"label": "Get dressed", "icon": "👕", "sort_order": 1},
            {"label": "Eat breakfast", "icon": "🥣", "sort_order": 2},
        ],
    }
    if profile_id:
        base["profile_id"] = str(profile_id)
    return base


# ── Tests ────────────────────────────────────────────────────────────────────


async def test_create_routine_with_steps(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    payload = _routine_payload(sample_household.id, sample_profile.id)
    resp = await authed_client.post("/api/routines", json=payload)
    assert resp.status_code == 201

    body = resp.json()
    assert body["name"] == "Morning Routine"
    assert body["time_block"] == "morning"
    assert len(body["steps"]) == 3
    assert body["steps"][0]["label"] == "Brush teeth"


async def test_list_routines(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    # Create a routine first
    await authed_client.post(
        "/api/routines",
        json=_routine_payload(sample_household.id, sample_profile.id),
    )

    resp = await authed_client.get(
        "/api/routines", params={"household_id": str(sample_household.id)}
    )
    assert resp.status_code == 200
    routines = resp.json()
    assert isinstance(routines, list)
    assert len(routines) >= 1
    assert routines[0]["name"] == "Morning Routine"


async def test_complete_step(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    # Create routine with steps
    create_resp = await authed_client.post(
        "/api/routines",
        json=_routine_payload(sample_household.id, sample_profile.id),
    )
    routine = create_resp.json()
    routine_id = routine["id"]
    step_id = routine["steps"][0]["id"]

    # Complete the first step
    resp = await authed_client.post(
        f"/api/routines/{routine_id}/steps/{step_id}/complete",
        params={"profile_id": str(sample_profile.id)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert step_id in body["completed_steps"]
    assert body["is_fully_completed"] is False


async def test_get_streak(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    # Create a routine
    create_resp = await authed_client.post(
        "/api/routines",
        json=_routine_payload(sample_household.id, sample_profile.id),
    )
    routine_id = create_resp.json()["id"]

    resp = await authed_client.get(
        f"/api/routines/{routine_id}/streak",
        params={"profile_id": str(sample_profile.id)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["current_streak"] == 0
    assert body["longest_streak"] == 0
    assert body["total_completions"] == 0
