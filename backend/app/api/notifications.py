"""API routes for reminders and notifications."""

import uuid
import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_profile
from app.database import get_db
from app.models.calendar import Event
from app.models.reminder import Reminder
from app.models.user import Profile
from app.schemas.reminder import ReminderCreate, ReminderResponse, UpcomingNotification

router = APIRouter(tags=["notifications"])


@router.post("/reminders", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    data: ReminderCreate,
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> Reminder:
    if current_profile.household_id != data.household_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Verify event exists and belongs to same household
    event = await db.get(Event, data.event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    fire_at = event.start_time - dt.timedelta(minutes=data.minutes_before)

    reminder = Reminder(
        event_id=data.event_id,
        household_id=data.household_id,
        minutes_before=data.minutes_before,
        fire_at=fire_at,
    )
    db.add(reminder)
    await db.flush()
    await db.refresh(reminder)
    return reminder


@router.get("/reminders", response_model=list[ReminderResponse])
async def list_reminders(
    event_id: uuid.UUID = Query(...),
    household_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> list[Reminder]:
    if current_profile.household_id != household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    result = await db.execute(
        select(Reminder)
        .where(Reminder.event_id == event_id, Reminder.household_id == household_id)
        .order_by(Reminder.fire_at)
    )
    return list(result.scalars().all())


@router.delete("/reminders/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(
    reminder_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> None:
    reminder = await db.get(Reminder, reminder_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    if reminder.household_id != current_profile.household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    await db.delete(reminder)
    await db.flush()


@router.get("/notifications/upcoming", response_model=list[UpcomingNotification])
async def get_upcoming_notifications(
    household_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> list[UpcomingNotification]:
    """Return reminders that should fire now or within the next 60 seconds."""
    if current_profile.household_id != household_id:
        raise HTTPException(status_code=403, detail="Access denied")

    now = dt.datetime.utcnow()
    window_end = now + dt.timedelta(seconds=60)

    result = await db.execute(
        select(Reminder, Event)
        .join(Event, Reminder.event_id == Event.id)
        .where(
            Reminder.household_id == household_id,
            Reminder.is_fired == False,  # noqa: E712
            Reminder.fire_at <= window_end,
        )
        .order_by(Reminder.fire_at)
    )

    notifications = []
    for reminder, event in result.all():
        # Mark as fired
        reminder.is_fired = True
        notifications.append(
            UpcomingNotification(
                reminder_id=reminder.id,
                event_id=event.id,
                event_title=event.title,
                event_start=event.start_time,
                minutes_before=reminder.minutes_before,
                fire_at=reminder.fire_at,
            )
        )

    if notifications:
        await db.flush()

    return notifications
