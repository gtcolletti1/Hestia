"""Tests for school-day awareness in routine windowing.

Covers:
- ``is_us_federal_holiday`` returns True for known federal holidays.
- A step flagged ``school_day_only`` is hidden on weekends, federal
  holidays, and admin-marked SchoolClosure dates.
- A routine whose only remaining applicable steps are school-day-only is
  treated as "no applicable steps today" on a non-school day, so it
  doesn't show up but also doesn't break a streak.
"""
from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.routine import Routine, RoutineStep, TimeBlock
from app.models.school_closure import SchoolClosure
from app.services.routine_window import (
    applicable_step_ids,
    routine_runs_today,
    step_applies_on,
)
from app.services.school_day import (
    is_us_federal_holiday,
    load_school_day_context,
)

pytestmark = pytest.mark.asyncio


def test_is_us_federal_holiday_known_dates():
    # Independence Day 2026 falls on a Saturday — but the date itself
    # is the holiday regardless of weekday.
    assert is_us_federal_holiday(date(2026, 7, 4)) is True
    assert is_us_federal_holiday(date(2026, 12, 25)) is True
    assert is_us_federal_holiday(date(2026, 1, 1)) is True
    # A random Tuesday in May should not be a federal holiday.
    assert is_us_federal_holiday(date(2026, 5, 5)) is False


async def test_school_day_context_handles_weekends_holidays_and_closures(
    db_session: AsyncSession, sample_household
):
    # Add a snow day for 2026-01-15 (a Thursday).
    db_session.add(
        SchoolClosure(
            household_id=sample_household.id,
            date=date(2026, 1, 15),
            reason="Snow day",
        )
    )
    await db_session.commit()

    ctx = await load_school_day_context(db_session, sample_household.id, 2026)

    # Weekday in May (no holiday) → school day.
    assert ctx.is_school_day(date(2026, 5, 5)) is True
    # Saturday → not a school day.
    assert ctx.is_school_day(date(2026, 5, 9)) is False
    # MLK Day 2026 → federal holiday → not a school day.
    assert ctx.is_school_day(date(2026, 1, 19)) is False
    # Manual snow day → not a school day.
    assert ctx.is_school_day(date(2026, 1, 15)) is False


def test_step_applies_on_respects_school_day_only_flag():
    # Build a step in-memory (no DB needed for the helper).
    step = RoutineStep(
        id=uuid.uuid4(),
        routine_id=uuid.uuid4(),
        label="Pack backpack",
        sort_order=0,
        days_of_week=[0, 1, 2, 3, 4],
        school_day_only=True,
    )
    # Mon-Fri school day → applies.
    assert step_applies_on(step, weekday=2, is_school_day=True) is True
    # Mon-Fri non-school day (e.g. Veterans Day on a Tuesday) → does NOT apply.
    assert step_applies_on(step, weekday=2, is_school_day=False) is False
    # Saturday — both: weekday gate fails too.
    assert step_applies_on(step, weekday=5, is_school_day=False) is False


async def test_routine_with_only_school_day_step_hidden_on_holiday(
    db_session: AsyncSession, sample_household
):
    routine = Routine(
        household_id=sample_household.id,
        name="Morning",
        time_block=TimeBlock.morning,
        days_of_week=[0, 1, 2, 3, 4],
    )
    db_session.add(routine)
    await db_session.flush()

    db_session.add(
        RoutineStep(
            routine_id=routine.id,
            label="Pack backpack",
            sort_order=0,
            school_day_only=True,
        )
    )
    await db_session.commit()
    await db_session.refresh(routine)
    # Reload steps via relationship.
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select as _sel

    routine = (
        await db_session.execute(
            _sel(Routine)
            .options(selectinload(Routine.steps))
            .where(Routine.id == routine.id)
        )
    ).scalar_one()

    weekday = 2  # Wednesday
    # On a normal school day → routine runs and has the one step applicable.
    assert routine_runs_today(routine, weekday, is_school_day=True) is True
    assert applicable_step_ids(routine, weekday, is_school_day=True) == {
        str(routine.steps[0].id)
    }
    # On a non-school day → no applicable steps → routine should not list.
    assert routine_runs_today(routine, weekday, is_school_day=False) is False
    assert applicable_step_ids(routine, weekday, is_school_day=False) == set()


def test_step_without_school_day_flag_unaffected():
    step = RoutineStep(
        id=uuid.uuid4(),
        routine_id=uuid.uuid4(),
        label="Brush teeth",
        sort_order=0,
        days_of_week=[0, 1, 2, 3, 4],
        school_day_only=False,
    )
    # Same step, school day or not — applies on weekdays in the gate.
    assert step_applies_on(step, weekday=2, is_school_day=True) is True
    assert step_applies_on(step, weekday=2, is_school_day=False) is True


def test_reason_for_returns_holiday_name_and_closure_reason():
    """``reason_for`` powers the splash/home banner: it returns the
    holiday name for federal holidays, the admin-supplied reason (or a
    generic fallback) for closures, and ``None`` for weekends and
    regular school days."""
    from app.services.school_day import SchoolDayContext

    ctx = SchoolDayContext(
        country="US",
        subdiv=None,
        year=2026,
        manual_closures={
            date(2026, 1, 15): "Snow day",
            date(2026, 3, 17): None,  # closure recorded without a reason
        },
    )

    # Holiday → human-readable name from the `holidays` package.
    mlk = ctx.reason_for(date(2026, 1, 19))
    assert mlk is not None and "Luther King" in mlk

    # Admin closure with reason.
    assert ctx.reason_for(date(2026, 1, 15)) == "Snow day"

    # Admin closure without reason → generic fallback.
    assert ctx.reason_for(date(2026, 3, 17)) == "School closure"

    # Weekend → no banner (None) even though it isn't a school day.
    assert ctx.reason_for(date(2026, 1, 17)) is None  # Saturday
    # Regular weekday → None.
    assert ctx.reason_for(date(2026, 5, 5)) is None
