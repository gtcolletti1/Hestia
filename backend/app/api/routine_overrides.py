"""Routine overrides API (Phase C parental override).

Admin-only endpoints for pausing routines, skipping a single day, and
toggling household-wide vacation mode. Overrides are consumed by
``app.services.routine_window`` to suppress affected routines from the
splash / dashboard / home views and to keep streaks intact across
intentional days off.
"""
from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_profile, require_admin
from app.database import get_db
from app.models.routine import Routine, RoutineOverride, RoutineOverrideKind
from app.models.user import Profile
from app.schemas.routine import RoutineOverrideCreate, RoutineOverrideResponse


router = APIRouter(tags=["routine-overrides"])


@router.post(
    "/routine-overrides",
    response_model=RoutineOverrideResponse,
    status_code=201,
)
async def create_routine_override(
    payload: RoutineOverrideCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: Profile = Depends(require_admin),
) -> RoutineOverride:
    if payload.kind == "skip":
        if payload.end_date is not None and payload.end_date != payload.start_date:
            raise HTTPException(
                status_code=422,
                detail="A 'skip' override is a single-day override; "
                "end_date must equal start_date or be omitted.",
            )
        end_date = payload.start_date
    else:
        if payload.end_date is not None and payload.end_date < payload.start_date:
            raise HTTPException(
                status_code=422,
                detail="end_date cannot be before start_date.",
            )
        end_date = payload.end_date

    if payload.routine_id is not None:
        routine = (
            await db.execute(
                select(Routine).where(Routine.id == payload.routine_id)
            )
        ).scalar_one_or_none()
        if routine is None:
            raise HTTPException(status_code=404, detail="Routine not found")
        if routine.household_id != current_admin.household_id:
            raise HTTPException(status_code=403, detail="Access denied")

    override = RoutineOverride(
        household_id=current_admin.household_id,
        routine_id=payload.routine_id,
        kind=RoutineOverrideKind(payload.kind),
        start_date=payload.start_date,
        end_date=end_date,
        reason=payload.reason,
        created_by_profile_id=current_admin.id,
    )
    db.add(override)
    await db.flush()
    await db.refresh(override)
    return override


@router.get(
    "/routine-overrides",
    response_model=list[RoutineOverrideResponse],
)
async def list_routine_overrides(
    household_id: uuid.UUID,
    routine_id: uuid.UUID | None = None,
    active_on: date | None = None,
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> list[RoutineOverride]:
    if current_profile.household_id != household_id:
        raise HTTPException(status_code=403, detail="Access denied")

    stmt = select(RoutineOverride).where(
        RoutineOverride.household_id == household_id
    )
    if routine_id is not None:
        stmt = stmt.where(RoutineOverride.routine_id == routine_id)
    if active_on is not None:
        stmt = stmt.where(
            RoutineOverride.start_date <= active_on,
            (RoutineOverride.end_date.is_(None))
            | (RoutineOverride.end_date >= active_on),
        )
    stmt = stmt.order_by(RoutineOverride.start_date.desc())
    return list((await db.execute(stmt)).scalars().all())


@router.delete("/routine-overrides/{override_id}", status_code=204)
async def delete_routine_override(
    override_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: Profile = Depends(require_admin),
) -> None:
    override = (
        await db.execute(
            select(RoutineOverride).where(RoutineOverride.id == override_id)
        )
    ).scalar_one_or_none()
    if override is None:
        raise HTTPException(status_code=404, detail="Override not found")
    if override.household_id != current_admin.household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    await db.delete(override)
    await db.flush()
