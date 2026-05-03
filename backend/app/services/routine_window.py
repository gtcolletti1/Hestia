"""Helpers for filtering routines to the current time block and excluding
routines already completed today.

Used by both the dashboard and splash endpoints so the visibility rules
stay consistent across views.
"""

from __future__ import annotations

import uuid
from datetime import date, time
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.routine import Routine, RoutineCompletion, TimeBlock


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


async def completed_routine_ids_today(
    db: AsyncSession,
    routines: Iterable[Routine],
    today: date,
) -> set[uuid.UUID]:
    """Return the set of routine ids that are fully completed today.

    For routines assigned to a profile, only completions by that profile
    count. For unassigned (household) routines, any household completion
    counts.
    """
    routines = list(routines)
    if not routines:
        return set()

    routine_ids = [r.id for r in routines]
    result = await db.execute(
        select(
            RoutineCompletion.routine_id,
            RoutineCompletion.profile_id,
        ).where(
            RoutineCompletion.routine_id.in_(routine_ids),
            RoutineCompletion.date == today,
            RoutineCompletion.is_fully_completed.is_(True),
        )
    )
    completions = result.all()

    # Map routine -> set of profile_ids that completed it today.
    by_routine: dict[uuid.UUID, set[uuid.UUID]] = {}
    for routine_id, profile_id in completions:
        by_routine.setdefault(routine_id, set()).add(profile_id)

    completed: set[uuid.UUID] = set()
    for r in routines:
        done_by = by_routine.get(r.id, set())
        if not done_by:
            continue
        if r.profile_id is None:
            # Unassigned: any completion counts.
            completed.add(r.id)
        elif r.profile_id in done_by:
            completed.add(r.id)
    return completed
