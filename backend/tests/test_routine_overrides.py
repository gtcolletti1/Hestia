"""Phase C: routine override tests (pause / skip / vacation mode)."""
from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.routine import (
    Routine,
    RoutineCompletion,
    RoutineOverride,
    RoutineOverrideKind,
    RoutineStep,
    TimeBlock,
)
from app.models.user import Household, Profile, ProfileRole
from app.services.routine_window import (
    compute_current_streak,
    load_active_overrides,
    routine_runs_today,
)

pytestmark = pytest.mark.asyncio


async def _make_daily_routine(
    db_session: AsyncSession,
    household: Household,
    profile: Profile,
    *,
    name: str = "Daily Tidy",
    pausable_on_vacation: bool = True,
) -> Routine:
    r = Routine(
        household_id=household.id,
        profile_id=profile.id,
        name=name,
        time_block=TimeBlock.morning,
        days_of_week=[0, 1, 2, 3, 4, 5, 6],
        is_active=True,
        pausable_on_vacation=pausable_on_vacation,
    )
    db_session.add(r)
    await db_session.flush()
    db_session.add(
        RoutineStep(routine_id=r.id, label="Tidy", sort_order=0)
    )
    await db_session.commit()
    return (
        await db_session.execute(
            select(Routine).options(selectinload(Routine.steps)).where(Routine.id == r.id)
        )
    ).scalar_one()


# ── routine_runs_today honors overrides ──────────────────────────────────────


async def test_routine_paused_is_hidden_today(
    db_session: AsyncSession,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    routine = await _make_daily_routine(db_session, sample_household, sample_profile)
    today = date.today()
    db_session.add(
        RoutineOverride(
            household_id=sample_household.id,
            routine_id=routine.id,
            kind=RoutineOverrideKind.pause,
            start_date=today - timedelta(days=1),
            end_date=today + timedelta(days=3),
        )
    )
    await db_session.commit()
    overrides = await load_active_overrides(db_session, sample_household.id, today)
    assert routine_runs_today(
        routine, today.weekday(), overrides=overrides, target=today
    ) is False


async def test_household_pause_skips_pausable_only(
    db_session: AsyncSession,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    pausable = await _make_daily_routine(
        db_session, sample_household, sample_profile, name="Brush Teeth"
    )
    medication = await _make_daily_routine(
        db_session,
        sample_household,
        sample_profile,
        name="Allergy Meds",
        pausable_on_vacation=False,
    )
    today = date.today()
    db_session.add(
        RoutineOverride(
            household_id=sample_household.id,
            routine_id=None,
            kind=RoutineOverrideKind.pause,
            start_date=today,
            end_date=today + timedelta(days=7),
            reason="Beach week",
        )
    )
    await db_session.commit()
    overrides = await load_active_overrides(db_session, sample_household.id, today)
    assert routine_runs_today(
        pausable, today.weekday(), overrides=overrides, target=today
    ) is False
    assert routine_runs_today(
        medication, today.weekday(), overrides=overrides, target=today
    ) is True


# ── Streak protection ───────────────────────────────────────────────────────


async def test_skip_today_does_not_break_streak(
    db_session: AsyncSession,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    routine = await _make_daily_routine(db_session, sample_household, sample_profile)
    today = date.today()
    step_id = str(routine.steps[0].id)

    # Build a 5-day streak ending yesterday.
    for offset in range(1, 6):
        d = today - timedelta(days=offset)
        db_session.add(
            RoutineCompletion(
                routine_id=routine.id,
                profile_id=sample_profile.id,
                date=d,
                completed_steps=[step_id],
                is_fully_completed=True,
            )
        )
    # Skip today.
    db_session.add(
        RoutineOverride(
            household_id=sample_household.id,
            routine_id=routine.id,
            kind=RoutineOverrideKind.skip,
            start_date=today,
            end_date=today,
            reason="Sick day",
        )
    )
    await db_session.commit()

    overrides = await load_active_overrides(db_session, sample_household.id, today)
    routine = (
        await db_session.execute(
            select(Routine).options(selectinload(Routine.steps)).where(Routine.id == routine.id)
        )
    ).scalar_one()
    streak = await compute_current_streak(
        db_session, routine, sample_profile.id, today, overrides=overrides
    )
    assert streak >= 5, f"skip-today must not break a 5-day streak; got {streak}"


# ── API: admin-only ──────────────────────────────────────────────────────────


async def test_create_override_requires_admin(
    async_client: AsyncClient,
    db_session: AsyncSession,
    sample_household: Household,
) -> None:
    # Make a kid profile and authenticate as them.
    kid = Profile(
        household_id=sample_household.id,
        name="Kid",
        color="#888888",
        role=ProfileRole.kid,
    )
    db_session.add(kid)
    await db_session.commit()

    from tests.conftest import _create_test_token
    token = _create_test_token(kid.id, role="kid")

    today = date.today()
    resp = await async_client.post(
        "/api/routine-overrides",
        json={
            "kind": "pause",
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=2)).isoformat(),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


async def test_admin_can_create_skip_today(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    today = date.today()
    resp = await authed_client.post(
        "/api/routine-overrides",
        json={
            "kind": "skip",
            "start_date": today.isoformat(),
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["kind"] == "skip"
    assert body["start_date"] == today.isoformat()
    assert body["end_date"] == today.isoformat()
