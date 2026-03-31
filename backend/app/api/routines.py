from __future__ import annotations
import uuid
from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.routine import Routine, RoutineCompletion, RoutineStep, TimeBlock
from app.schemas.routine import (
    RoutineCompletionResponse,
    RoutineCreate,
    RoutineResponse,
    RoutineUpdate,
    StreakInfo,
)

router = APIRouter(tags=["routines"])

TIME_BLOCK_RANGES: dict[TimeBlock, tuple[time, time]] = {
    TimeBlock.morning: (time(5, 0), time(11, 59)),
    TimeBlock.afternoon: (time(12, 0), time(16, 59)),
    TimeBlock.evening: (time(17, 0), time(20, 59)),
    TimeBlock.bedtime: (time(21, 0), time(23, 59)),
}


# ── List routines ────────────────────────────────────────────────────────────


@router.get("/routines", response_model=list[RoutineResponse])
async def list_routines(
    household_id: uuid.UUID = Query(...),
    profile_id: uuid.UUID | None = Query(None),
    time_block: TimeBlock | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> list[Routine]:
    stmt = (
        select(Routine)
        .options(selectinload(Routine.steps))
        .where(Routine.household_id == household_id)
        .order_by(Routine.sort_order)
    )
    if profile_id is not None:
        stmt = stmt.where(Routine.profile_id == profile_id)
    if time_block is not None:
        stmt = stmt.where(Routine.time_block == time_block)
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ── Active routines (current time + day of week) ────────────────────────────


@router.get("/routines/active", response_model=list[RoutineResponse])
async def get_active_routines(
    household_id: uuid.UUID = Query(...),
    profile_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> list[Routine]:
    now = datetime.now()
    current_day = now.weekday()
    current_time = now.time()

    current_block: TimeBlock | None = None
    for block, (start, end) in TIME_BLOCK_RANGES.items():
        if start <= current_time <= end:
            current_block = block
            break

    stmt = (
        select(Routine)
        .options(selectinload(Routine.steps))
        .where(
            Routine.household_id == household_id,
            Routine.is_active.is_(True),
        )
        .order_by(Routine.sort_order)
    )
    if profile_id is not None:
        stmt = stmt.where(Routine.profile_id == profile_id)
    if current_block is not None:
        stmt = stmt.where(Routine.time_block == current_block)

    result = await db.execute(stmt)
    routines = result.scalars().all()

    return [r for r in routines if current_day in (r.days_of_week or [])]


# ── Get routine ──────────────────────────────────────────────────────────────


@router.get("/routines/{routine_id}", response_model=RoutineResponse)
async def get_routine(
    routine_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Routine:
    stmt = (
        select(Routine)
        .options(selectinload(Routine.steps))
        .where(Routine.id == routine_id)
    )
    result = await db.execute(stmt)
    routine = result.scalar_one_or_none()
    if routine is None:
        raise HTTPException(status_code=404, detail="Routine not found")
    return routine


# ── Create routine ───────────────────────────────────────────────────────────


@router.post("/routines", response_model=RoutineResponse, status_code=201)
async def create_routine(
    payload: RoutineCreate,
    db: AsyncSession = Depends(get_db),
) -> Routine:
    routine = Routine(
        household_id=payload.household_id,
        profile_id=payload.profile_id,
        name=payload.name,
        time_block=payload.time_block,
        days_of_week=payload.days_of_week,
        start_time=payload.start_time,
        is_active=payload.is_active,
    )
    db.add(routine)
    await db.flush()

    for step_data in payload.steps:
        step = RoutineStep(
            routine_id=routine.id,
            label=step_data.label,
            icon=step_data.icon,
            sort_order=step_data.sort_order,
        )
        db.add(step)

    await db.flush()

    # Reload with steps
    stmt = (
        select(Routine)
        .options(selectinload(Routine.steps))
        .where(Routine.id == routine.id)
    )
    result = await db.execute(stmt)
    return result.scalar_one()


# ── Update routine ───────────────────────────────────────────────────────────


@router.put("/routines/{routine_id}", response_model=RoutineResponse)
async def update_routine(
    routine_id: uuid.UUID,
    payload: RoutineUpdate,
    db: AsyncSession = Depends(get_db),
) -> Routine:
    stmt = (
        select(Routine)
        .options(selectinload(Routine.steps))
        .where(Routine.id == routine_id)
    )
    result = await db.execute(stmt)
    routine = result.scalar_one_or_none()
    if routine is None:
        raise HTTPException(status_code=404, detail="Routine not found")

    update_data = payload.model_dump(exclude_unset=True)
    steps_data = update_data.pop("steps", None)

    for field, value in update_data.items():
        setattr(routine, field, value)

    # Replace steps if provided
    if steps_data is not None:
        for existing_step in list(routine.steps):
            await db.delete(existing_step)
        await db.flush()

        for step_data in steps_data:
            step = RoutineStep(
                routine_id=routine.id,
                label=step_data["label"],
                icon=step_data.get("icon"),
                sort_order=step_data["sort_order"],
            )
            db.add(step)

    await db.flush()

    # Reload
    stmt = (
        select(Routine)
        .options(selectinload(Routine.steps))
        .where(Routine.id == routine.id)
    )
    result = await db.execute(stmt)
    return result.scalar_one()


# ── Delete routine ───────────────────────────────────────────────────────────


@router.delete("/routines/{routine_id}", status_code=204)
async def delete_routine(
    routine_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    stmt = select(Routine).where(Routine.id == routine_id)
    result = await db.execute(stmt)
    routine = result.scalar_one_or_none()
    if routine is None:
        raise HTTPException(status_code=404, detail="Routine not found")
    await db.delete(routine)


# ── Complete a step ──────────────────────────────────────────────────────────


@router.post(
    "/routines/{routine_id}/steps/{step_id}/complete",
    response_model=RoutineCompletionResponse,
)
async def complete_step(
    routine_id: uuid.UUID,
    step_id: uuid.UUID,
    profile_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
) -> RoutineCompletion:
    # Verify routine and step exist
    stmt = (
        select(Routine)
        .options(selectinload(Routine.steps))
        .where(Routine.id == routine_id)
    )
    result = await db.execute(stmt)
    routine = result.scalar_one_or_none()
    if routine is None:
        raise HTTPException(status_code=404, detail="Routine not found")

    step_ids = {str(s.id) for s in routine.steps}
    if str(step_id) not in step_ids:
        raise HTTPException(status_code=404, detail="Step not found in this routine")

    today = date.today()

    # Upsert completion record for today
    stmt = select(RoutineCompletion).where(
        RoutineCompletion.routine_id == routine_id,
        RoutineCompletion.profile_id == profile_id,
        RoutineCompletion.date == today,
    )
    result = await db.execute(stmt)
    completion = result.scalar_one_or_none()

    if completion is None:
        completion = RoutineCompletion(
            routine_id=routine_id,
            profile_id=profile_id,
            date=today,
            completed_steps=[],
        )
        db.add(completion)
        await db.flush()

    # Add step if not already completed
    step_id_str = str(step_id)
    if step_id_str not in completion.completed_steps:
        completion.completed_steps = [*completion.completed_steps, step_id_str]

    # Check if all steps are done
    if set(completion.completed_steps) >= step_ids:
        completion.is_fully_completed = True
        completion.completed_at = datetime.now()

    await db.flush()
    await db.refresh(completion)
    return completion


# ── Streak info ──────────────────────────────────────────────────────────────


@router.get("/routines/{routine_id}/streak", response_model=StreakInfo)
async def get_streak(
    routine_id: uuid.UUID,
    profile_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
) -> StreakInfo:
    stmt = (
        select(RoutineCompletion)
        .where(
            RoutineCompletion.routine_id == routine_id,
            RoutineCompletion.profile_id == profile_id,
            RoutineCompletion.is_fully_completed.is_(True),
        )
        .order_by(RoutineCompletion.date.desc())
    )
    result = await db.execute(stmt)
    completions = result.scalars().all()

    total_completions = len(completions)
    if total_completions == 0:
        return StreakInfo(current_streak=0, longest_streak=0, total_completions=0)

    dates = [c.date for c in completions]

    # Calculate current streak (consecutive days ending today or yesterday)
    current_streak = 0
    today = date.today()
    expected = today
    for d in dates:
        if d == expected:
            current_streak += 1
            expected = date.fromordinal(d.toordinal() - 1)
        elif d < expected:
            # Allow gap: if most recent completion is yesterday, still count
            if current_streak == 0 and d == date.fromordinal(today.toordinal() - 1):
                current_streak = 1
                expected = date.fromordinal(d.toordinal() - 1)
            else:
                break

    # Calculate longest streak
    longest_streak = 1
    streak = 1
    for i in range(1, len(dates)):
        if dates[i].toordinal() == dates[i - 1].toordinal() - 1:
            streak += 1
            longest_streak = max(longest_streak, streak)
        else:
            streak = 1

    longest_streak = max(longest_streak, current_streak)

    return StreakInfo(
        current_streak=current_streak,
        longest_streak=longest_streak,
        total_completions=total_completions,
    )
