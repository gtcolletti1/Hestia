"""API routes for the Dashboard composite endpoint."""


import uuid
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_profile
from app.database import get_db
from app.models.list import ListItem, TaskList
from app.models.meal import MealPlan
from app.models.routine import Routine, RoutineCompletion
from sqlalchemy.orm import selectinload
from app.models.user import Household, Profile
from app.schemas.dashboard import (
    ActiveListSummary,
    AgendaBucket,
    DashboardResponse,
    EventSummary,
    ProfileSummary,
    VacationStatus,
)
from app.services.event_expansion import expand_events_in_range
from app.services.routine_window import (
    applicable_step_ids,
    routine_runs_today,
    completed_routine_ids_today,
    compute_current_streak,
    household_vacation_on,
    load_active_overrides,
    current_time_block,
)
from app.services.school_day import load_school_day_context

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    household_id: uuid.UUID = Query(...),
    tz: str | None = Query(
        None,
        description=(
            "IANA timezone name (e.g. 'America/New_York') used to compute "
            "'today' for the agenda. Falls back to UTC if missing or invalid."
        ),
    ),
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> DashboardResponse:
    """Composite read-only dashboard endpoint."""
    if current_profile.household_id != household_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Resolve the household's display timezone. Priority order:
    #   1. The household's stored 'timezone' setting (admin-configurable),
    #   2. the optional `tz` query param the browser sends as a fallback
    #      auto-detect, and finally
    #   3. UTC. We log when we fall through so a misconfigured deployment
    #      surfaces in the backend log instead of a wrong-bucket UI.
    household = (
        await db.execute(select(Household).where(Household.id == household_id))
    ).scalar_one_or_none()
    candidate_zones: list[str] = []
    if household and isinstance(household.settings, dict):
        stored = household.settings.get("timezone")
        if stored:
            candidate_zones.append(stored)
    if tz:
        candidate_zones.append(tz)

    local_tz: ZoneInfo | timezone = timezone.utc
    for zone_name in candidate_zones:
        try:
            local_tz = ZoneInfo(zone_name)
            break
        except (ZoneInfoNotFoundError, ValueError):
            continue

    now_local = datetime.now(tz=local_tz)
    today = now_local.date()
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
    # Build the day window in the household's local zone, then convert to
    # UTC for the SQL filter. Events stored in UTC will be matched only if
    # they actually fall on the local "today".
    day_start_local = datetime.combine(today, time.min, tzinfo=local_tz)
    day_end_local = day_start_local + timedelta(days=1)
    day_start = day_start_local.astimezone(timezone.utc)
    day_end = day_end_local.astimezone(timezone.utc)

    events_stmt_expanded = await expand_events_in_range(
        db,
        household_id,
        day_start,
        day_end,
    )

    morning_events: list[EventSummary] = []
    afternoon_events: list[EventSummary] = []
    evening_events: list[EventSummary] = []

    noon = time(12, 0)
    five_pm = time(17, 0)

    for occ in events_stmt_expanded:
        event = occ.event
        summary = EventSummary(
            id=event.id,
            title=event.title,
            start_time=occ.start_time,
            end_time=occ.end_time,
            color=event.color,
            profile_name=occ.profile_name,
            location=event.location,
        )
        # Bucket using the event's local time in the household's zone, not
        # UTC — otherwise a 7pm-EDT event (23:00 UTC) lands in "morning".
        event_local_time = occ.start_time.astimezone(local_tz).time()
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
    # Show only routines for today's weekday + the current time block.
    # Drop routines already fully completed today so the list reflects
    # what actually still needs doing.
    active_block = current_time_block(now.astimezone(local_tz).time())
    routines_result = await db.execute(
        select(Routine)
        .options(selectinload(Routine.steps))
        .where(
            Routine.household_id == household_id,
            Routine.is_active.is_(True),
            Routine.time_block == active_block,
        )
    )
    overrides = await load_active_overrides(db, household_id, today)
    school_ctx = await load_school_day_context(db, household_id, today.year)
    today_is_school = school_ctx.is_school_day(today)
    todays_routines = [
        r for r in routines_result.scalars().all()
        if routine_runs_today(
            r,
            current_weekday,
            overrides=overrides,
            target=today,
            is_school_day=today_is_school,
        )
    ]
    completed_ids = await completed_routine_ids_today(
        db, todays_routines, today, is_school_day=today_is_school
    )

    # Compute consecutive-day streak per routine (only when assigned).
    active_routines: list[dict] = []
    for routine in todays_routines:
        if routine.id in completed_ids:
            continue
        streak = 0
        if routine.profile_id is not None:
            streak = await compute_current_streak(
                db,
                routine,
                routine.profile_id,
                today,
                overrides=overrides,
                school_day_ctx=school_ctx,
            )
        # Show the count of steps actually applicable today, not the
        # routine's full step library — a Mon-Fri "Pack backpack" step
        # shouldn't be counted on Sundays or school holidays.
        applicable_count = len(
            applicable_step_ids(
                routine, current_weekday, is_school_day=today_is_school
            )
        )
        active_routines.append(
            {
                "id": str(routine.id),
                "name": routine.name,
                "time_block": routine.time_block.value,
                "profile_id": str(routine.profile_id) if routine.profile_id else None,
                "step_count": applicable_count,
                "streak_days": streak,
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
        vacation=(
            VacationStatus(
                active=True,
                reason=vac.reason,
                end_date=vac.end_date,
            )
            if (vac := household_vacation_on(overrides, today)) is not None
            else None
        ),
    )
