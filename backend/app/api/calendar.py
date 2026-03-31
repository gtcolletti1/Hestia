import uuid
from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.calendar import Event, SourceCalendar
from app.schemas.calendar import (
    EventCreate,
    EventResponse,
    EventUpdate,
    SourceCalendarCreate,
    SourceCalendarResponse,
    SourceCalendarUpdate,
)

router = APIRouter(tags=["calendar"])


# ── Events ───────────────────────────────────────────────────────────────────


@router.get("/events", response_model=list[EventResponse])
async def list_events(
    household_id: uuid.UUID,
    start_date: date,
    end_date: date,
    profile_id: uuid.UUID | None = None,
    source_calendar_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[Event]:
    range_start = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    range_end = datetime.combine(end_date, time.max, tzinfo=timezone.utc)

    stmt = (
        select(Event)
        .join(SourceCalendar, Event.source_calendar_id == SourceCalendar.id)
        .where(
            SourceCalendar.household_id == household_id,
            Event.start_time <= range_end,
            Event.end_time >= range_start,
        )
    )

    if profile_id is not None:
        stmt = stmt.where(Event.profile_id == profile_id)
    if source_calendar_id is not None:
        stmt = stmt.where(Event.source_calendar_id == source_calendar_id)

    result = await db.execute(stmt.order_by(Event.start_time))
    return list(result.scalars().all())


@router.get("/events/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Event:
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


@router.post("/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    data: EventCreate,
    db: AsyncSession = Depends(get_db),
) -> Event:
    calendar = await db.get(SourceCalendar, data.source_calendar_id)
    if not calendar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Source calendar not found"
        )

    event = Event(**data.model_dump())
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event


@router.put("/events/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: uuid.UUID,
    data: EventUpdate,
    db: AsyncSession = Depends(get_db),
) -> Event:
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(event, field, value)

    await db.flush()
    await db.refresh(event)
    return event


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    await db.delete(event)
    await db.flush()


# ── Source Calendars ─────────────────────────────────────────────────────────


@router.get("/calendars", response_model=list[SourceCalendarResponse])
async def list_calendars(
    household_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[SourceCalendar]:
    result = await db.execute(
        select(SourceCalendar).where(SourceCalendar.household_id == household_id)
    )
    return list(result.scalars().all())


@router.post("/calendars", response_model=SourceCalendarResponse, status_code=status.HTTP_201_CREATED)
async def create_calendar(
    data: SourceCalendarCreate,
    db: AsyncSession = Depends(get_db),
) -> SourceCalendar:
    cal = SourceCalendar(**data.model_dump())
    db.add(cal)
    await db.flush()
    await db.refresh(cal)
    return cal


@router.put("/calendars/{calendar_id}", response_model=SourceCalendarResponse)
async def update_calendar(
    calendar_id: uuid.UUID,
    data: SourceCalendarUpdate,
    db: AsyncSession = Depends(get_db),
) -> SourceCalendar:
    cal = await db.get(SourceCalendar, calendar_id)
    if not cal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(cal, field, value)

    await db.flush()
    await db.refresh(cal)
    return cal


@router.delete("/calendars/{calendar_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_calendar(
    calendar_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    cal = await db.get(SourceCalendar, calendar_id)
    if not cal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found")
    await db.delete(cal)
    await db.flush()
