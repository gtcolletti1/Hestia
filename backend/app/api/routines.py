import uuid
from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.auth import get_current_profile
from app.database import get_db
from app.models.routine import Routine, RoutineCompletion, RoutineStep, TimeBlock
from app.models.reward import PointLedger
from app.models.user import Profile
from app.schemas.routine import (
    RoutineCompletionResponse,
    RoutineCreate,
    RoutineResponse,
    RoutineTemplateResponse,
    RoutineUpdate,
    StreakInfo,
)
from app.data.routine_templates import ROUTINE_TEMPLATES

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
    current_profile: Profile = Depends(get_current_profile),
) -> list[Routine]:
    if current_profile.household_id != household_id:
        raise HTTPException(status_code=403, detail="Access denied")
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
    current_profile: Profile = Depends(get_current_profile),
) -> list[Routine]:
    if current_profile.household_id != household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    now = datetime.now(timezone.utc)
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


@router.get("/routines/templates", response_model=list[RoutineTemplateResponse])
async def list_routine_templates(
    current_profile: Profile = Depends(get_current_profile),
) -> list[dict]:
    """Return the curated list of pre-built routine templates.

    Templates are static suggestions; the frontend uses one to pre-fill
    the New Routine form, then saves via the normal POST /routines path.
    Auth is required to keep the API surface uniform with the rest of
    the routines namespace.
    """
    return ROUTINE_TEMPLATES


@router.get("/routines/{routine_id}", response_model=RoutineResponse)
async def get_routine(
    routine_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
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
    if routine.household_id != current_profile.household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return routine


# ── Create routine ───────────────────────────────────────────────────────────


@router.post("/routines", response_model=RoutineResponse, status_code=201)
async def create_routine(
    payload: RoutineCreate,
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> Routine:
    if current_profile.household_id != payload.household_id:
        raise HTTPException(status_code=403, detail="Access denied")
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
            points_value=step_data.points_value,
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
    current_profile: Profile = Depends(get_current_profile),
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
    if routine.household_id != current_profile.household_id:
        raise HTTPException(status_code=403, detail="Access denied")

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
                points_value=step_data.get("points_value", 0),
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
    current_profile: Profile = Depends(get_current_profile),
) -> None:
    stmt = select(Routine).where(Routine.id == routine_id)
    result = await db.execute(stmt)
    routine = result.scalar_one_or_none()
    if routine is None:
        raise HTTPException(status_code=404, detail="Routine not found")
    if routine.household_id != current_profile.household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    await db.delete(routine)
    await db.flush()


# ── Duplicate routine ────────────────────────────────────────────────────────


@router.post("/routines/{routine_id}/duplicate", response_model=RoutineResponse, status_code=201)
async def duplicate_routine(
    routine_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> Routine:
    """Clone a routine and all its steps. The copy is named 'Copy of {name}'."""
    stmt = (
        select(Routine)
        .options(selectinload(Routine.steps))
        .where(Routine.id == routine_id)
    )
    result = await db.execute(stmt)
    original = result.scalar_one_or_none()
    if original is None:
        raise HTTPException(status_code=404, detail="Routine not found")
    if original.household_id != current_profile.household_id:
        raise HTTPException(status_code=403, detail="Access denied")

    copy = Routine(
        household_id=original.household_id,
        profile_id=original.profile_id,
        name=f"Copy of {original.name}",
        time_block=original.time_block,
        days_of_week=list(original.days_of_week) if original.days_of_week else [],
        start_time=original.start_time,
        is_active=original.is_active,
    )
    db.add(copy)
    await db.flush()

    for step in sorted(original.steps, key=lambda s: s.sort_order):
        db.add(RoutineStep(
            routine_id=copy.id,
            label=step.label,
            icon=step.icon,
            sort_order=step.sort_order,
            points_value=step.points_value,
        ))

    await db.flush()

    # Reload with steps
    stmt = (
        select(Routine)
        .options(selectinload(Routine.steps))
        .where(Routine.id == copy.id)
    )
    result = await db.execute(stmt)
    return result.scalar_one()


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
    current_profile: Profile = Depends(get_current_profile),
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
    if routine.household_id != current_profile.household_id:
        raise HTTPException(status_code=403, detail="Access denied")

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

        # Award points if the step has a point value
        completed_step = next((s for s in routine.steps if str(s.id) == step_id_str), None)
        if completed_step and completed_step.points_value > 0:
            ledger_entry = PointLedger(
                household_id=routine.household_id,
                profile_id=profile_id,
                points=completed_step.points_value,
                reason=f"Completed: {completed_step.label}",
                routine_step_id=step_id,
            )
            db.add(ledger_entry)

    # Check if all steps are done
    if set(completion.completed_steps) >= step_ids:
        completion.is_fully_completed = True
        completion.completed_at = datetime.utcnow()

    await db.flush()
    await db.refresh(completion)
    return completion


# ── Streak info ──────────────────────────────────────────────────────────────


@router.get("/routines/{routine_id}/streak", response_model=StreakInfo)
async def get_streak(
    routine_id: uuid.UUID,
    profile_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> StreakInfo:
    routine = await db.get(Routine, routine_id)
    if routine is None:
        raise HTTPException(status_code=404, detail="Routine not found")
    if routine.household_id != current_profile.household_id:
        raise HTTPException(status_code=403, detail="Access denied")

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
        elif current_streak == 0 and d == date.fromordinal(today.toordinal() - 1):
            # Most recent completion was yesterday — start streak from there
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
