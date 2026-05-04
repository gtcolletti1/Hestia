"""Tests for per-step chore assignment (RoutineStep.assigned_profile_id).

PRD ref: US-2.3.8 (Per-Step Chore Assignment).
"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Household, Profile, ProfileRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture()
async def sibling_profile(
    db_session: AsyncSession, sample_household: Household
) -> Profile:
    """A second non-admin profile inside the same household."""
    p = Profile(
        household_id=sample_household.id,
        name="Sibling",
        color="#33A1FF",
        role=ProfileRole.kid,
        pin_hash=pwd_context.hash("4321"),
        is_active=True,
    )
    db_session.add(p)
    await db_session.flush()
    await db_session.refresh(p)
    return p


def _routine_payload(
    household_id: uuid.UUID,
    *,
    profile_id: uuid.UUID | None = None,
    step_assignees: list[uuid.UUID | None] | None = None,
) -> dict:
    if step_assignees is None:
        step_assignees = [None]
    steps = []
    for i, assignee in enumerate(step_assignees):
        s = {"label": f"Step {i+1}", "sort_order": i}
        if assignee is not None:
            s["assigned_profile_id"] = str(assignee)
        steps.append(s)
    body: dict = {
        "household_id": str(household_id),
        "name": "Test Routine",
        "time_block": "morning",
        "days_of_week": [0, 1, 2, 3, 4, 5, 6],
        "school_day_only": False,
        "steps": steps,
    }
    if profile_id is not None:
        body["profile_id"] = str(profile_id)
    return body


# ── Validation ───────────────────────────────────────────────────────────────


async def test_assignee_must_belong_to_same_household(
    authed_client: AsyncClient,
    sample_household: Household,
    second_profile: Profile,
) -> None:
    """A step cannot be assigned to a profile in another household."""
    resp = await authed_client.post(
        "/api/routines",
        json=_routine_payload(
            sample_household.id, step_assignees=[second_profile.id]
        ),
    )
    assert resp.status_code == 400


async def test_assignee_must_match_routine_profile_when_set(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
    sibling_profile: Profile,
) -> None:
    """If routine.profile_id=Alex, a step cannot be assigned to Sibling."""
    resp = await authed_client.post(
        "/api/routines",
        json=_routine_payload(
            sample_household.id,
            profile_id=sample_profile.id,
            step_assignees=[sibling_profile.id],
        ),
    )
    assert resp.status_code == 400


async def test_household_routine_persists_assignee(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
    sibling_profile: Profile,
) -> None:
    """Steps in a household routine can be split across profiles."""
    resp = await authed_client.post(
        "/api/routines",
        json=_routine_payload(
            sample_household.id,
            step_assignees=[sample_profile.id, sibling_profile.id, None],
        ),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assignees = [s.get("assigned_profile_id") for s in body["steps"]]
    assert assignees[0] == str(sample_profile.id)
    assert assignees[1] == str(sibling_profile.id)
    assert assignees[2] is None


# ── Pre-existing bug fix: school_day_only persistence ───────────────────────


async def test_school_day_only_persists_through_create(
    authed_client: AsyncClient,
    sample_household: Household,
) -> None:
    """Regression: school_day_only on a step was previously dropped on create."""
    body = _routine_payload(sample_household.id)
    body["steps"][0]["school_day_only"] = True
    resp = await authed_client.post("/api/routines", json=body)
    assert resp.status_code == 201, resp.text
    assert resp.json()["steps"][0]["school_day_only"] is True


# ── Authorization on complete_step ───────────────────────────────────────────


async def test_wrong_profile_cannot_complete_assigned_step(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
    sibling_profile: Profile,
) -> None:
    """Profile B gets a 403 when trying to complete a step assigned to A."""
    create = await authed_client.post(
        "/api/routines",
        json=_routine_payload(
            sample_household.id, step_assignees=[sample_profile.id]
        ),
    )
    assert create.status_code == 201
    routine = create.json()
    step_id = routine["steps"][0]["id"]

    # Sibling tries to complete Admin's step → 403.
    resp = await authed_client.post(
        f"/api/routines/{routine['id']}/steps/{step_id}/complete",
        params={"profile_id": str(sibling_profile.id)},
    )
    assert resp.status_code == 403

    # Admin (assignee) succeeds.
    ok = await authed_client.post(
        f"/api/routines/{routine['id']}/steps/{step_id}/complete",
        params={"profile_id": str(sample_profile.id)},
    )
    assert ok.status_code == 200, ok.text
