"""API routes for reminders and notifications."""

import uuid
import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, or_, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_profile
from app.database import get_db
from app.models.calendar import Event
from app.models.notification import NotificationEntry
from app.models.reminder import Reminder
from app.models.user import Profile
from app.schemas.reminder import (
    InboxEntry,
    InboxUnreadCount,
    ReminderCreate,
    ReminderResponse,
    UpcomingNotification,
)

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
        # Persist to the notification inbox so the bell can show history.
        # Household-wide entry (profile_id=NULL) — reminders apply to anyone
        # at the wall display.
        db.add(
            NotificationEntry(
                household_id=household_id,
                profile_id=None,
                kind="reminder",
                title=event.title,
                body=f"Starts in {reminder.minutes_before} min",
                link_url=f"/calendar?event={event.id}",
            )
        )

    if notifications:
        await db.flush()

    return notifications


# ── Inbox (notification bell history) ───────────────────────────────────────


def _inbox_filter(
    household_id: uuid.UUID, profile_id: uuid.UUID
):
    """Build the WHERE clause matching entries visible to a profile.

    Profile sees:
      - household-wide entries (profile_id IS NULL)
      - entries explicitly addressed to them
    """
    return (
        (NotificationEntry.household_id == household_id)
        & or_(
            NotificationEntry.profile_id.is_(None),
            NotificationEntry.profile_id == profile_id,
        )
    )


@router.get("/notifications/inbox", response_model=list[InboxEntry])
async def list_inbox(
    household_id: uuid.UUID = Query(...),
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> list[NotificationEntry]:
    if current_profile.household_id != household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    stmt = (
        select(NotificationEntry)
        .where(_inbox_filter(household_id, current_profile.id))
        .order_by(NotificationEntry.created_at.desc())
        .limit(limit)
    )
    if unread_only:
        stmt = stmt.where(NotificationEntry.read_at.is_(None))
    return list((await db.execute(stmt)).scalars().all())


@router.get(
    "/notifications/inbox/unread_count", response_model=InboxUnreadCount
)
async def inbox_unread_count(
    household_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> InboxUnreadCount:
    if current_profile.household_id != household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    stmt = (
        select(func.count(NotificationEntry.id))
        .where(_inbox_filter(household_id, current_profile.id))
        .where(NotificationEntry.read_at.is_(None))
    )
    n = (await db.execute(stmt)).scalar_one() or 0
    return InboxUnreadCount(unread=int(n))


@router.post(
    "/notifications/inbox/{entry_id}/read",
    response_model=InboxEntry,
)
async def mark_inbox_entry_read(
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> NotificationEntry:
    entry = await db.get(NotificationEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    if entry.household_id != current_profile.household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    if (
        entry.profile_id is not None
        and entry.profile_id != current_profile.id
    ):
        raise HTTPException(status_code=403, detail="Access denied")
    if entry.read_at is None:
        entry.read_at = dt.datetime.utcnow()
        await db.flush()
        await db.refresh(entry)
    return entry


@router.post("/notifications/inbox/mark_all_read", response_model=InboxUnreadCount)
async def mark_all_inbox_read(
    household_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> InboxUnreadCount:
    if current_profile.household_id != household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    now = dt.datetime.utcnow()
    await db.execute(
        update(NotificationEntry)
        .where(_inbox_filter(household_id, current_profile.id))
        .where(NotificationEntry.read_at.is_(None))
        .values(read_at=now)
    )
    await db.flush()
    return InboxUnreadCount(unread=0)
