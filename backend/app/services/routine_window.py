"""Helpers for filtering routines to the current time block and excluding
routines already completed today, plus the per-step day-of-week scheduling
logic that drives both the stepper UI and the streak rule.

Used by both the dashboard and splash endpoints so the visibility rules
stay consistent across views.
"""

from __future__ import annotations

import uuid
from datetime import date, time, timedelta
from typing import Iterable

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


async def load_active_overrides(
    db: AsyncSession, household_id: uuid.UUID, today: date
) -> list[RoutineOverride]:
    """All overrides for the household that are active at any point on
    ``today`` or later, capped to a ~1-year window. Used to filter the
    splash/dashboard *and* to drive the streak walk-back so paused days
    don't break a streak.
    """
    horizon = today - timedelta(days=366)
    result = await db.execute(
        select(RoutineOverride).where(
            RoutineOverride.household_id == household_id,
            RoutineOverride.start_date <= today + timedelta(days=30),
            (RoutineOverride.end_date.is_(None))
            | (RoutineOverride.end_date >= horizon),
        )
    )
    return list(result.scalars().all())


def routine_paused_on(
    routine: Routine,
    overrides: Iterable[RoutineOverride],
    target: date,
) -> RoutineOverride | None:
    """Return the first override that suppresses ``routine`` on ``target``,
    or None. Household-wide overrides only apply when the routine is
    ``pausable_on_vacation``.
    """
    for ov in overrides:
        if not ov.covers(target):
            continue
        if ov.routine_id is None:
            if not routine.pausable_on_vacation:
                continue
            return ov
        if ov.routine_id == routine.id:
            return ov
    return None


def household_vacation_on(
    overrides: Iterable[RoutineOverride], target: date
) -> RoutineOverride | None:
    """Return the active household-wide *pause* override covering
    ``target``, if any. Skip-today overrides and per-routine overrides
    are ignored — this is just for the 🏝 banner on home/splash.
    """
    for ov in overrides:
        if ov.routine_id is not None:
            continue
        if ov.kind != RoutineOverrideKind.pause:
            continue
        if ov.covers(target):
            return ov
    return None


def current_time_block(local_time: time) -> TimeBlock:
    """Return the time block the given local clock time falls in.

    Mirrors the frontend's bucketing in RoutineList.currentTimeBlock so
    the home/splash views and the routines tab agree on what's "now".
    """
    h = local_time.hour
    if 5 <= h < 12:
        return TimeBlock.morning
    if 12 <= h < 17:
        return TimeBlock.afternoon
    if 17 <= h < 21:
        return TimeBlock.evening
    return TimeBlock.bedtime


def step_applies_on(step: RoutineStep, weekday: int) -> bool:
    """Whether ``step`` runs on ``weekday`` (0=Mon..6=Sun).

    A step with NULL/empty ``days_of_week`` runs on every day the routine
    runs — that's the default and matches pre-Phase-B behavior.
    """
    dow = step.days_of_week
    if not dow:
        return True
    return weekday in dow


def applicable_step_ids(routine: Routine, weekday: int) -> set[str]:
    """IDs (as str) of steps in ``routine`` that apply on ``weekday``."""
    return {str(s.id) for s in routine.steps if step_applies_on(s, weekday)}


def is_routine_complete_for(
    routine: Routine, weekday: int, completed_step_ids: Iterable[str]
) -> bool:
    """True iff every step applicable on ``weekday`` is in ``completed_step_ids``.

    If the routine has no applicable steps for the day (e.g. all steps are
    weekday-only and it's Sunday), this returns False — the routine should
    not have been listed for that day in the first place.
    """
    needed = applicable_step_ids(routine, weekday)
    if not needed:
        return False
    return needed.issubset(set(completed_step_ids))


def routine_runs_today(
    routine: Routine,
    weekday: int,
    *,
    overrides: Iterable[RoutineOverride] | None = None,
    target: date | None = None,
) -> bool:
    """Should this routine be listed for ``weekday``?

    True when the routine's day-of-week gate includes the weekday AND
    either it has no steps at all (legacy / placeholder routine) or at
    least one step is applicable today AND no active override covers it.
    """
    if weekday not in (routine.days_of_week or []):
        return False
    if overrides is not None and target is not None:
        if routine_paused_on(routine, overrides, target) is not None:
            return False
    if not routine.steps:
        return True
    return bool(applicable_step_ids(routine, weekday))


async def completed_routine_ids_today(
    db: AsyncSession,
    routines: Iterable[Routine],
    today: date,
) -> set[uuid.UUID]:
    """Return the set of routine ids that are fully completed today.

    A routine is "fully completed" when all of its applicable steps for
    today's weekday are in some matching ``RoutineCompletion.completed_steps``
    list. For routines assigned to a profile, only completions by that
    profile count. For unassigned (household) routines, any household
    completion that satisfies the applicable-step set counts.
    """
    routines = list(routines)
    if not routines:
        return set()

    routine_ids = [r.id for r in routines]
    weekday = today.weekday()

    # Map (routine_id, profile_id) -> (completed step ids, any is_fully_completed flag)
    by_key: dict[tuple[uuid.UUID, uuid.UUID], set[str]] = {}
    full_flag: dict[tuple[uuid.UUID, uuid.UUID], bool] = {}
    result2 = await db.execute(
        select(
            RoutineCompletion.routine_id,
            RoutineCompletion.profile_id,
            RoutineCompletion.completed_steps,
            RoutineCompletion.is_fully_completed,
        ).where(
            RoutineCompletion.routine_id.in_(routine_ids),
            RoutineCompletion.date == today,
        )
    )
    for routine_id, profile_id, steps, fully in result2.all():
        by_key.setdefault((routine_id, profile_id), set()).update(steps or [])
        if fully:
            full_flag[(routine_id, profile_id)] = True

    completed: set[uuid.UUID] = set()
    for r in routines:
        needed = applicable_step_ids(r, weekday)
        if not r.steps:
            # Legacy step-less routine: rely on is_fully_completed flag.
            if r.profile_id is None:
                done = any(
                    flag for (rid, _pid), flag in full_flag.items() if rid == r.id
                )
            else:
                done = full_flag.get((r.id, r.profile_id), False)
            if done:
                completed.add(r.id)
            continue
        if not needed:
            continue
        if r.profile_id is None:
            # Unassigned: any single profile that completed the applicable
            # set counts as done for the household view.
            done = any(
                steps >= needed
                for (rid, _pid), steps in by_key.items()
                if rid == r.id
            )
        else:
            steps = by_key.get((r.id, r.profile_id), set())
            done = steps >= needed
        if done:
            completed.add(r.id)
    return completed


async def compute_current_streak(
    db: AsyncSession,
    routine: Routine,
    profile_id: uuid.UUID,
    today: date,
    max_lookback_days: int = 366,
    *,
    overrides: Iterable[RoutineOverride] | None = None,
) -> int:
    """Walk backwards across the routine's *scheduled* days, counting
    consecutive days where every applicable step was completed.

    Override-suppressed days (paused / skipped) behave exactly like
    non-scheduled days: they are skipped in the walk-back, neither
    extending nor breaking the streak. So a holiday week off doesn't
    nuke a 30-day streak.
    """
    scheduled = list(routine.days_of_week or [])
    if not scheduled:
        return 0
    overrides_list = list(overrides) if overrides is not None else []

    earliest = today - timedelta(days=max_lookback_days)
    result = await db.execute(
        select(RoutineCompletion.date, RoutineCompletion.completed_steps)
        .where(
            RoutineCompletion.routine_id == routine.id,
            RoutineCompletion.profile_id == profile_id,
            RoutineCompletion.date >= earliest,
            RoutineCompletion.date <= today,
        )
    )
    by_date: dict[date, set[str]] = {
        d: set(steps or []) for d, steps in result.all()
    }

    def is_complete(d: date) -> bool:
        return is_routine_complete_for(routine, d.weekday(), by_date.get(d, set()))

    def is_paused(d: date) -> bool:
        return routine_paused_on(routine, overrides_list, d) is not None

    streak = 0
    cursor = today
    today_scheduled = today.weekday() in scheduled and not is_paused(today)
    today_done = today_scheduled and is_complete(today)

    if today_scheduled and not today_done:
        cursor = today - timedelta(days=1)

    while cursor >= earliest:
        if cursor.weekday() in scheduled and not is_paused(cursor):
            if is_complete(cursor):
                streak += 1
                cursor = cursor - timedelta(days=1)
                continue
            break
        cursor = cursor - timedelta(days=1)
    return streak
