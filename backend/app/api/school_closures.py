"""School closures CRUD API.

Admin-only writes; any household member can read. Combines with the
built-in US federal holiday list (via `app.services.school_day`) to
decide whether routine steps flagged ``school_day_only`` apply on a
given date.
"""
from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_profile, require_admin
from app.database import get_db
from app.models.school_closure import SchoolClosure
from app.models.user import Profile
from app.schemas.school_closure import (
    SchoolClosureCreate,
    SchoolClosureResponse,
)


router = APIRouter(tags=["school-closures"])


@router.post(
    "/school-closures",
    response_model=SchoolClosureResponse,
    status_code=201,
)
async def create_school_closure(
    payload: SchoolClosureCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: Profile = Depends(require_admin),
) -> SchoolClosure:
    if payload.household_id != current_admin.household_id:
        raise HTTPException(status_code=403, detail="Access denied")

    closure = SchoolClosure(
        household_id=payload.household_id,
        date=payload.date,
        reason=payload.reason,
        created_by_profile_id=current_admin.id,
    )
    db.add(closure)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"A school closure already exists for {payload.date}.",
        )
    await db.refresh(closure)
    return closure


@router.get(
    "/school-closures",
    response_model=list[SchoolClosureResponse],
)
async def list_school_closures(
    household_id: uuid.UUID,
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> list[SchoolClosure]:
    if current_profile.household_id != household_id:
        raise HTTPException(status_code=403, detail="Access denied")

    stmt = select(SchoolClosure).where(SchoolClosure.household_id == household_id)
    if start_date is not None:
        stmt = stmt.where(SchoolClosure.date >= start_date)
    if end_date is not None:
        stmt = stmt.where(SchoolClosure.date <= end_date)
    stmt = stmt.order_by(SchoolClosure.date.asc())
    return list((await db.execute(stmt)).scalars().all())


@router.delete("/school-closures/{closure_id}", status_code=204)
async def delete_school_closure(
    closure_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: Profile = Depends(require_admin),
) -> None:
    closure = (
        await db.execute(
            select(SchoolClosure).where(SchoolClosure.id == closure_id)
        )
    ).scalar_one_or_none()
    if closure is None:
        raise HTTPException(status_code=404, detail="Closure not found")
    if closure.household_id != current_admin.household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    await db.delete(closure)
    await db.flush()
