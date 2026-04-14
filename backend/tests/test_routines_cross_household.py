"""Cross-household access tests for routines endpoints."""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.models.user import Household, Profile

pytestmark = pytest.mark.asyncio


# ── Helpers ──────────────────────────────────────────────────────────────────


def _routine_payload(household_id: str, profile_id: str | None = None) -> dict:
    base = {
        "household_id": household_id,
        "name": "Morning Routine",
        "time_block": "morning",
        "days_of_week": [0, 1, 2, 3, 4],
        "steps": [
            {"label": "Brush teeth", "icon": "🪥", "sort_order": 0},
            {"label": "Get dressed", "icon": "👕", "sort_order": 1},
        ],
    }
    if profile_id:
        base["profile_id"] = profile_id
    return base


async def _create_routine(client: AsyncClient, household_id: str, profile_id: str) -> dict:
    """Create a routine and return the full response body."""
    resp = await client.post(
        "/api/routines",
        json=_routine_payload(household_id, profile_id),
    )
    assert resp.status_code == 201
    return resp.json()


# ── Cross-household tests ────────────────────────────────────────────────────


async def test_cross_household_list_routines(
    authed_client: AsyncClient,
    second_authed_client: AsyncClient,
    sample_household: Household,
) -> None:
    """User from household B cannot list household A's routines."""
    resp = await second_authed_client.get(
        "/api/routines",
        params={"household_id": str(sample_household.id)},
    )
    assert resp.status_code == 403


async def test_cross_household_list_active_routines(
    authed_client: AsyncClient,
    second_authed_client: AsyncClient,
    sample_household: Household,
) -> None:
    """User from household B cannot list household A's active routines."""
    resp = await second_authed_client.get(
        "/api/routines/active",
        params={"household_id": str(sample_household.id)},
    )
    assert resp.status_code == 403


async def test_cross_household_get_routine(
    authed_client: AsyncClient,
    second_authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """User from household B cannot get a specific routine from household A."""
    routine = await _create_routine(
        authed_client, str(sample_household.id), str(sample_profile.id)
    )

    resp = await second_authed_client.get(f"/api/routines/{routine['id']}")
    assert resp.status_code == 403


async def test_cross_household_create_routine(
    second_authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """User from household B cannot create a routine in household A."""
    resp = await second_authed_client.post(
        "/api/routines",
        json=_routine_payload(str(sample_household.id), str(sample_profile.id)),
    )
    assert resp.status_code == 403


async def test_cross_household_update_routine(
    authed_client: AsyncClient,
    second_authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """User from household B cannot update household A's routine."""
    routine = await _create_routine(
        authed_client, str(sample_household.id), str(sample_profile.id)
    )

    resp = await second_authed_client.put(
        f"/api/routines/{routine['id']}",
        json={"name": "Tampered Routine"},
    )
    assert resp.status_code == 403


async def test_cross_household_delete_routine(
    authed_client: AsyncClient,
    second_authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """User from household B cannot delete household A's routine."""
    routine = await _create_routine(
        authed_client, str(sample_household.id), str(sample_profile.id)
    )

    resp = await second_authed_client.delete(f"/api/routines/{routine['id']}")
    assert resp.status_code == 403


async def test_cross_household_complete_step(
    authed_client: AsyncClient,
    second_authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
    second_profile: Profile,
) -> None:
    """User from household B cannot complete a step on household A's routine."""
    routine = await _create_routine(
        authed_client, str(sample_household.id), str(sample_profile.id)
    )
    step_id = routine["steps"][0]["id"]

    resp = await second_authed_client.post(
        f"/api/routines/{routine['id']}/steps/{step_id}/complete",
        params={"profile_id": str(second_profile.id)},
    )
    assert resp.status_code == 403


async def test_cross_household_get_streak(
    authed_client: AsyncClient,
    second_authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
    second_profile: Profile,
) -> None:
    """User from household B cannot view streak for household A's routine."""
    routine = await _create_routine(
        authed_client, str(sample_household.id), str(sample_profile.id)
    )

    resp = await second_authed_client.get(
        f"/api/routines/{routine['id']}/streak",
        params={"profile_id": str(second_profile.id)},
    )
    assert resp.status_code == 403
