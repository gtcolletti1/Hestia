import uuid
from datetime import date, datetime, time, timedelta, timezone

from dateutil.rrule import rrulestr
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_profile
from app.database import get_db
from app.models.calendar import Event, SourceCalendar
from app.models.user import Profile
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
    current_profile: Profile = Depends(get_current_profile),
) -> list[EventResponse]:
    if current_profile.household_id != household_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    range_start = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    range_end = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)

    stmt = (
        select(Event)
        .join(SourceCalendar, Event.source_calendar_id == SourceCalendar.id)
        .where(
            SourceCalendar.household_id == household_id,
            Event.start_time < range_end,
            Event.end_time >= range_start,
        )
    )

    if profile_id is not None:
        stmt = stmt.where(Event.profile_id == profile_id)
    if source_calendar_id is not None:
        stmt = stmt.where(Event.source_calendar_id == source_calendar_id)

    result = await db.execute(stmt.order_by(Event.start_time))
    db_events = list(result.scalars().all())

    # Also fetch recurring events that START before our range (they may generate occurrences within it)
    recur_stmt = (
        select(Event)
        .join(SourceCalendar, Event.source_calendar_id == SourceCalendar.id)
        .where(
            SourceCalendar.household_id == household_id,
            Event.recurrence_rule.isnot(None),
            Event.start_time < range_end,
        )
    )
    if profile_id is not None:
        recur_stmt = recur_stmt.where(Event.profile_id == profile_id)
    if source_calendar_id is not None:
        recur_stmt = recur_stmt.where(Event.source_calendar_id == source_calendar_id)

    recur_result = await db.execute(recur_stmt)
    recurring_events = list(recur_result.scalars().all())

    # Deduplicate (recurring events in range already appear in db_events)
    seen_ids = {e.id for e in db_events}
    output: list[EventResponse] = []

    # Add non-recurring events as-is
    for ev in db_events:
        if not ev.recurrence_rule:
            output.append(EventResponse.model_validate(ev))

    # Expand recurring events into occurrences
    for ev in recurring_events:
        if ev.id not in seen_ids:
            seen_ids.add(ev.id)

        duration = ev.end_time - ev.start_time
        try:
            rule = rrulestr(ev.recurrence_rule, dtstart=ev.start_time, ignoretz=True)
            occurrences = rule.between(
                range_start.replace(tzinfo=None),
                range_end.replace(tzinfo=None),
                inc=True,
            )
        except (ValueError, TypeError):
            # If the RRULE is malformed, just return the original event
            ev_start = ev.start_time if ev.start_time.tzinfo else ev.start_time.replace(tzinfo=timezone.utc)
            ev_end = ev.end_time if ev.end_time.tzinfo else ev.end_time.replace(tzinfo=timezone.utc)
            if ev_start < range_end and ev_end >= range_start:
                output.append(EventResponse.model_validate(ev))
            continue

        for occ_start_naive in occurrences:
            occ_start = occ_start_naive.replace(tzinfo=timezone.utc)
            occ_end = occ_start + duration
            output.append(
                EventResponse(
                    id=ev.id,
                    source_calendar_id=ev.source_calendar_id,
                    profile_id=ev.profile_id,
                    external_id=ev.external_id,
                    title=ev.title,
                    description=ev.description,
                    location=ev.location,
                    start_time=occ_start,
                    end_time=occ_end,
                    all_day=ev.all_day,
                    recurrence_rule=ev.recurrence_rule,
                    color=ev.color,
                    is_private=ev.is_private,
                    created_at=ev.created_at,
                    updated_at=ev.updated_at,
                )
            )

    output.sort(key=lambda e: e.start_time)
    return output


@router.get("/events/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> Event:
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    calendar = await db.get(SourceCalendar, event.source_calendar_id)
    if not calendar or calendar.household_id != current_profile.household_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return event


@router.post("/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    data: EventCreate,
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> Event:
    calendar = await db.get(SourceCalendar, data.source_calendar_id)
    if not calendar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Source calendar not found"
        )
    if calendar.household_id != current_profile.household_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

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
    current_profile: Profile = Depends(get_current_profile),
) -> Event:
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    calendar = await db.get(SourceCalendar, event.source_calendar_id)
    if not calendar or calendar.household_id != current_profile.household_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(event, field, value)

    await db.flush()
    await db.refresh(event)
    return event


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> None:
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    calendar = await db.get(SourceCalendar, event.source_calendar_id)
    if not calendar or calendar.household_id != current_profile.household_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    await db.delete(event)
    await db.flush()


# ── Source Calendars ─────────────────────────────────────────────────────────


@router.get("/calendars", response_model=list[SourceCalendarResponse])
async def list_calendars(
    household_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> list[SourceCalendar]:
    if current_profile.household_id != household_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    result = await db.execute(
        select(SourceCalendar).where(SourceCalendar.household_id == household_id)
    )
    return list(result.scalars().all())


@router.post("/calendars", response_model=SourceCalendarResponse, status_code=status.HTTP_201_CREATED)
async def create_calendar(
    data: SourceCalendarCreate,
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> SourceCalendar:
    if current_profile.household_id != data.household_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
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
    current_profile: Profile = Depends(get_current_profile),
) -> SourceCalendar:
    cal = await db.get(SourceCalendar, calendar_id)
    if not cal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found")
    if cal.household_id != current_profile.household_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(cal, field, value)

    await db.flush()
    await db.refresh(cal)
    return cal


@router.delete("/calendars/{calendar_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_calendar(
    calendar_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> None:
    cal = await db.get(SourceCalendar, calendar_id)
    if not cal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found")
    if cal.household_id != current_profile.household_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    await db.delete(cal)
    await db.flush()
