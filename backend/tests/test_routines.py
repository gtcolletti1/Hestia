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


# ── Phase B: per-step days_of_week + scheduled-day streak ────────────────────


async def test_step_days_of_week_persisted(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    payload = _routine_payload(sample_household.id, sample_profile.id)
    payload["days_of_week"] = [0, 1, 2, 3, 4, 5, 6]
    payload["steps"] = [
        {"label": "Brush teeth", "sort_order": 0},
        {"label": "Pack backpack", "sort_order": 1, "days_of_week": [0, 1, 2, 3, 4]},
    ]
    resp = await authed_client.post("/api/routines", json=payload)
    assert resp.status_code == 201
    steps = resp.json()["steps"]
    by_label = {s["label"]: s for s in steps}
    assert by_label["Brush teeth"]["days_of_week"] is None
    assert by_label["Pack backpack"]["days_of_week"] == [0, 1, 2, 3, 4]


async def test_routine_complete_when_only_applicable_steps_done(
    authed_client: AsyncClient,
    db_session: AsyncSession,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """On a non-school day, completing the everyday steps marks the
    routine fully complete even though the weekday-only step isn't done.
    """
    from datetime import date as _date
    from app.models.routine import RoutineCompletion as _RC
    from app.services.routine_window import is_routine_complete_for

    today = _date.today()
    # Build the routine to *include* today, with one weekday-only step
    # and one every-day step.
    weekday_only = [d for d in range(7) if d != today.weekday()][:5]
    payload = _routine_payload(sample_household.id, sample_profile.id)
    payload["days_of_week"] = list(range(7))
    payload["steps"] = [
        {"label": "Always", "sort_order": 0},
        {"label": "Other days only", "sort_order": 1, "days_of_week": weekday_only},
    ]
    resp = await authed_client.post("/api/routines", json=payload)
    assert resp.status_code == 201
    routine_id = resp.json()["id"]
    always_step_id = next(
        s["id"] for s in resp.json()["steps"] if s["label"] == "Always"
    )

    # Complete the everyday step.
    resp = await authed_client.post(
        f"/api/routines/{routine_id}/steps/{always_step_id}/complete",
        params={"profile_id": str(sample_profile.id)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_fully_completed"] is True


async def test_weekend_only_streak_continues_across_weekends(
    authed_client: AsyncClient,
    db_session: AsyncSession,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """A Sat/Sun-only routine should be able to streak >2 by skipping weekdays."""
    from datetime import date as _date, timedelta as _td
    from app.models.routine import Routine as _R, RoutineStep as _RS, RoutineCompletion as _RC
    from app.services.routine_window import compute_current_streak

    today = _date.today()
    # Build a Sat/Sun-only routine.
    routine = _R(
        household_id=sample_household.id,
        profile_id=sample_profile.id,
        name="Weekend Tidy",
        time_block=TimeBlock.morning,
        days_of_week=[5, 6],
        is_active=True,
    )
    db_session.add(routine)
    await db_session.flush()
    step = _RS(
        routine_id=routine.id, label="Tidy room", sort_order=0
    )
    db_session.add(step)
    await db_session.flush()

    # Find the most recent Sat (5) and Sun (6) over the past several weeks
    # and complete each. Walk back ~28 days.
    weekend_dates = [
        today - _td(days=i)
        for i in range(28)
        if (today - _td(days=i)).weekday() in (5, 6)
        and (today - _td(days=i)) <= today
    ]
    for d in weekend_dates:
        db_session.add(
            _RC(
                routine_id=routine.id,
                profile_id=sample_profile.id,
                date=d,
                completed_steps=[str(step.id)],
                is_fully_completed=True,
            )
        )
    await db_session.commit()
    # Re-fetch with steps eager-loaded for the streak walker.
    from sqlalchemy import select as _select
    from sqlalchemy.orm import selectinload as _sel
    routine = (
        await db_session.execute(
            _select(_R).options(_sel(_R.steps)).where(_R.id == routine.id)
        )
    ).scalar_one()

    streak = await compute_current_streak(db_session, routine, sample_profile.id, today)
    # Should count every consecutive scheduled (Sat/Sun) day going back.
    assert streak >= len(weekend_dates), (
        f"expected streak >= {len(weekend_dates)}, got {streak}"
    )
