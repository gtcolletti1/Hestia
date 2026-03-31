"""API routes for the Dashboard composite endpoint."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.calendar import Event, SourceCalendar
from app.models.list import ListItem, TaskList
from app.models.meal import MealPlan
from app.models.routine import Routine
from app.models.user import Profile
from app.schemas.dashboard import (
    ActiveListSummary,
    AgendaBucket,
    DashboardResponse,
    EventSummary,
    ProfileSummary,
)

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    household_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    """Composite read-only dashboard endpoint."""
    today = date.today()
    now = datetime.now(tz=timezone.utc)
    current_weekday = today.weekday()  # Monday = 0

    # ── Profiles ─────────────────────────────────────────────────────────
    profiles_result = await db.execute(
        select(Profile).where(
            Profile.household_id == household_id,
            Profile.is_active.is_(True),
        )
    )
    profiles = [
        ProfileSummary.model_validate(p) for p in profiles_result.scalars().all()
    ]

    # ── Today's events ───────────────────────────────────────────────────
    day_start = datetime.combine(today, time.min, tzinfo=timezone.utc)
    day_end = datetime.combine(today, time.max, tzinfo=timezone.utc)

    events_stmt = (
        select(Event, Profile.name.label("profile_name"))
        .join(SourceCalendar, Event.source_calendar_id == SourceCalendar.id)
        .outerjoin(Profile, Event.profile_id == Profile.id)
        .where(
            SourceCalendar.household_id == household_id,
            Event.start_time <= day_end,
            Event.end_time >= day_start,
        )
        .order_by(Event.start_time)
    )
    events_result = await db.execute(events_stmt)
    rows = events_result.all()

    morning_events: list[EventSummary] = []
    afternoon_events: list[EventSummary] = []
    evening_events: list[EventSummary] = []

    noon = time(12, 0)
    five_pm = time(17, 0)

    for event, profile_name in rows:
        summary = EventSummary(
            id=event.id,
            title=event.title,
            start_time=event.start_time,
            end_time=event.end_time,
            color=event.color,
            profile_name=profile_name,
            location=event.location,
        )
        event_local_time = event.start_time.timetz()
        if event_local_time < noon:
            morning_events.append(summary)
        elif event_local_time < five_pm:
            afternoon_events.append(summary)
        else:
            evening_events.append(summary)

    agenda = [
        AgendaBucket(bucket="morning", events=morning_events),
        AgendaBucket(bucket="afternoon", events=afternoon_events),
        AgendaBucket(bucket="evening", events=evening_events),
    ]

    # ── Active routines ──────────────────────────────────────────────────
    routines_result = await db.execute(
        select(Routine).where(
            Routine.household_id == household_id,
            Routine.is_active.is_(True),
        )
    )
    active_routines: list[dict] = []
    current_time = now.timetz()

    for routine in routines_result.scalars().all():
        if current_weekday not in (routine.days_of_week or []):
            continue
        active_routines.append(
            {
                "id": str(routine.id),
                "name": routine.name,
                "time_block": routine.time_block.value,
                "profile_id": str(routine.profile_id) if routine.profile_id else None,
            }
        )

    # ── Today's meals ────────────────────────────────────────────────────
    meals_result = await db.execute(
        select(MealPlan)
        .where(
            MealPlan.household_id == household_id,
            MealPlan.date == today,
        )
        .order_by(MealPlan.meal_type)
    )
    today_meals = meals_result.scalars().all()

    # ── Active lists ─────────────────────────────────────────────────────
    lists_stmt = (
        select(
            TaskList.id,
            TaskList.name,
            func.count(ListItem.id).label("item_count"),
            func.count(ListItem.id).filter(ListItem.is_checked.is_(True)).label("checked_count"),
        )
        .outerjoin(ListItem, ListItem.list_id == TaskList.id)
        .where(
            TaskList.household_id == household_id,
            TaskList.is_archived.is_(False),
        )
        .group_by(TaskList.id)
    )
    lists_result = await db.execute(lists_stmt)
    active_lists = [
        ActiveListSummary(
            id=row.id,
            name=row.name,
            item_count=row.item_count,
            checked_count=row.checked_count,
        )
        for row in lists_result.all()
    ]

    return DashboardResponse(
        date=today,
        profiles=profiles,
        agenda=agenda,
        active_routines=active_routines,
        today_meals=today_meals,
        active_lists=active_lists,
    )
