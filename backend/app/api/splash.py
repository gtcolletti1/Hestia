"""Public, unauthenticated splash endpoint (PRD §2.12).

This is the **security boundary** for the pre-login privacy policy. The
admin's chosen disclosure rules (``splash_calendar_mode`` plus the
``splash_show_*`` toggles) are enforced *here*, server-side, before any
data leaves the host. Hidden sections must never appear in the response,
and obscured fields must never be present even at debug levels — a
client cannot leak what it never receives.
"""
from __future__ import annotations

import datetime as dt
import uuid
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.meal import MealPlan
from app.models.note import Note
from app.models.routine import Routine, RoutineCompletion
from app.models.user import Household, Profile
from app.schemas.admin import HouseholdSettings
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
from app.schemas.splash import (
    SplashClock,
    SplashDay,
    SplashEvent,
    SplashMeal,
    SplashMessage,
    SplashPolicy,
    SplashResponse,
    SplashRoutine,
    SplashRoutineAssignee,
    SplashVacation,
)


router = APIRouter(tags=["splash"])


# Default settings used when a household has no settings stored yet.
# Mirrors app/api/admin.py — kept independent so the splash route does
# not depend on any admin-route helper that may grow auth assumptions.
_DEFAULT_SETTINGS = HouseholdSettings(name="").model_dump()


def _load_settings(household: Household) -> HouseholdSettings:
    stored = household.settings or {}
    merged = {**_DEFAULT_SETTINGS, **stored, "name": household.name}
    return HouseholdSettings(**merged)


def _resolve_tz(name: str) -> ZoneInfo | timezone:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return timezone.utc


def _day_label(target: date, today: date) -> str:
    delta = (target - today).days
    if delta == 0:
        return "Today"
    if delta == 1:
        return "Tomorrow"
    return target.strftime("%A")


async def _resolve_household(
    db: AsyncSession, household_id: uuid.UUID | None
) -> Household:
    """Find the household the splash should render for.

    Hestia is a single-household appliance (PRD §2.9.3), so the typical
    splash request omits ``household_id`` entirely — we pick the lone
    household. The query parameter remains supported for legacy callers
    and tests that create multiple households.
    """
    if household_id is not None:
        h = await db.get(Household, household_id)
        if h is None:
            raise HTTPException(status_code=404, detail="Household not found")
        return h

    result = await db.execute(
        select(Household).order_by(Household.created_at).limit(2)
    )
    households = result.scalars().all()
    if not households:
        raise HTTPException(status_code=404, detail="No household configured")
    if len(households) > 1:
        # Multi-household appliances are out of scope for v2.x; require an
        # explicit ID rather than guess.
        raise HTTPException(
            status_code=400,
            detail="Multiple households exist; pass ?household_id= to disambiguate",
        )
    return households[0]


async def _build_days(
    db: AsyncSession,
    household_id: uuid.UUID,
    local_tz: ZoneInfo | timezone,
    today: date,
    max_days: int,
    calendar_mode: str,
) -> list[SplashDay]:
    """Return today + N upcoming days of agenda.

    Spill into upcoming days is bounded by ``max_days``. The viewport-fit
    truncation lives in the frontend (US-2.12.2): the API is happy to
    return all ``max_days`` worth of data and let the client hide what
    doesn't fit. Returning more than the cap would defeat the policy
    knob, so the server enforces it strictly.
    """
    if calendar_mode == "hidden":  # Defensive: caller already filters this
        return []

    range_start_local = datetime.combine(today, time.min, tzinfo=local_tz)
    range_end_local = range_start_local + timedelta(days=max_days)
    range_start = range_start_local.astimezone(timezone.utc)
    range_end = range_end_local.astimezone(timezone.utc)

    expanded = await expand_events_in_range(
        db,
        household_id,
        range_start,
        range_end,
    )

    days: list[SplashDay] = []
    for offset in range(max_days):
        d = today + timedelta(days=offset)
        d_start_local = datetime.combine(d, time.min, tzinfo=local_tz)
        d_end_local = d_start_local + timedelta(days=1)
        d_start = d_start_local.astimezone(timezone.utc)
        d_end = d_end_local.astimezone(timezone.utc)

        events: list[SplashEvent] = []
        for occ in expanded:
            event = occ.event
            start = occ.start_time
            end = occ.end_time
            if not (start < d_end and end > d_start):
                continue

            if calendar_mode == "busy_only":
                # Strip everything a passerby shouldn't see. We deliberately
                # do not echo the original title even into a hidden field —
                # the response object literally never contains it.
                events.append(
                    SplashEvent(
                        id=event.id,
                        title="Busy",
                        start_time=start,
                        end_time=end,
                        color=None,  # source-calendar color can identify the calendar
                        profile_color=occ.profile_color,
                        profile_name=None,
                        location=None,
                        all_day=bool(getattr(event, "all_day", False)),
                    )
                )
            else:
                events.append(
                    SplashEvent(
                        id=event.id,
                        title=event.title,
                        start_time=start,
                        end_time=end,
                        color=event.color,
                        profile_color=occ.profile_color,
                        profile_name=occ.profile_name,
                        location=event.location,
                        all_day=bool(getattr(event, "all_day", False)),
                    )
                )

        days.append(SplashDay(date=d, label=_day_label(d, today), events=events))

    return days


async def _build_routines(
    db: AsyncSession,
    household_id: uuid.UUID,
    today: date,
    current_weekday: int,
    active_block,
) -> list[SplashRoutine]:
    routines_result = await db.execute(
        select(Routine)
        .options(selectinload(Routine.steps), selectinload(Routine.profile))
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
    routines = [r for r in todays_routines if r.id not in completed_ids]

    # One streak walk per active routine. The set of "today" routines
    # is small (usually < 10) so the N+1 is acceptable; if it grows we
    # can batch with a window function.
    out: list[SplashRoutine] = []
    for r in routines:
        streak = 0
        if r.profile_id is not None:
            streak = await compute_current_streak(
                db,
                r,
                r.profile_id,
                today,
                overrides=overrides,
                school_day_ctx=school_ctx,
            )

        if r.profile is not None:
            assignee = SplashRoutineAssignee(
                id=r.profile.id,
                name=r.profile.name,
                color=r.profile.color,
                avatar_url=r.profile.avatar_url,
            )
        else:
            assignee = SplashRoutineAssignee(name="Household")

        out.append(
            SplashRoutine(
                id=r.id,
                name=r.name,
                time_block=r.time_block.value,
                step_count=len(
                    applicable_step_ids(
                        r, current_weekday, is_school_day=today_is_school
                    )
                ),
                streak_days=streak,
                assignee=assignee,
            )
        )

    return out


async def _build_meals(
    db: AsyncSession, household_id: uuid.UUID, today: date
) -> list[SplashMeal]:
    result = await db.execute(
        select(MealPlan)
        .where(MealPlan.household_id == household_id, MealPlan.date == today)
        .order_by(MealPlan.meal_type)
    )
    return [
        SplashMeal(id=m.id, meal_type=m.meal_type.value, title=m.title)
        for m in result.scalars().all()
    ]


async def _build_messages(
    db: AsyncSession, household_id: uuid.UUID
) -> list[SplashMessage]:
    """Pinned-first, then most recent; capped at 5 to keep the splash readable."""
    result = await db.execute(
        select(Note, Profile.name.label("author_name"))
        .outerjoin(Profile, Note.author_profile_id == Profile.id)
        .where(Note.household_id == household_id)
        .order_by(Note.pinned.desc(), Note.created_at.desc())
        .limit(5)
    )
    out: list[SplashMessage] = []
    for note, author in result.all():
        out.append(
            SplashMessage(
                id=note.id,
                title=note.title or "",
                body=note.body or "",
                pinned=bool(note.pinned),
                color=getattr(note, "color", None),
                author_name=author,
                created_at=note.created_at,
            )
        )
    return out


@router.get("/splash", response_model=SplashResponse, response_model_exclude_none=False)
async def get_splash(
    response: Response,
    household_id: uuid.UUID | None = Query(
        default=None,
        description=(
            "Optional. Omit on a single-household appliance (the default); "
            "supply when multiple households coexist."
        ),
    ),
    db: AsyncSession = Depends(get_db),
) -> SplashResponse:
    """Public, **unauthenticated** composite endpoint for the splash.

    The admin disclosure policy is applied here. Hidden sections are
    omitted (the field is ``None``); obscured calendar items have their
    sensitive fields stripped before serialization.
    """
    household = await _resolve_household(db, household_id)
    settings = _load_settings(household)

    local_tz = _resolve_tz(settings.timezone)
    now_local = datetime.now(tz=local_tz)
    today = now_local.date()
    iso_now = datetime.now(tz=timezone.utc)
    current_weekday = today.weekday()

    days: list[SplashDay] | None
    if settings.splash_calendar_mode == "hidden":
        days = None
    else:
        days = await _build_days(
            db,
            household.id,
            local_tz,
            today,
            settings.splash_agenda_max_days,
            settings.splash_calendar_mode,
        )

    routines: list[SplashRoutine] | None = None
    if settings.splash_show_routines:
        active_block = current_time_block(now_local.time())
        routines = await _build_routines(
            db, household.id, today, current_weekday, active_block
        )

    # Vacation banner — surface an active household-wide pause so the
    # splash can explain why pausable routines are missing today. Loaded
    # unconditionally (cheap) so the banner appears even when the
    # routines block is hidden by policy.
    overrides_today = await load_active_overrides(db, household.id, today)
    vac = household_vacation_on(overrides_today, today)
    vacation: SplashVacation | None = (
        SplashVacation(
            active=True,
            reason=vac.reason,
            end_date=vac.end_date,
        )
        if vac is not None
        else None
    )

    meals: list[SplashMeal] | None = None
    if settings.splash_show_meals:
        meals = await _build_meals(db, household.id, today)

    messages: list[SplashMessage] | None = None
    if settings.splash_show_messages:
        messages = await _build_messages(db, household.id)

    # Weather: when configured, we fetch live conditions server-side
    # so the splash doesn't need a second (authenticated) round-trip
    # to /api/weather. Failures are swallowed to a "available=false"
    # state — we never want a flaky upstream to break the splash.
    weather = None
    if settings.splash_show_weather:
        from app.schemas.splash import SplashWeather  # local import avoids cycles
        configured = (
            settings.weather_lat is not None and settings.weather_lon is not None
        )
        weather = SplashWeather(
            available=configured,
            units=settings.weather_units,
        )
        if configured:
            from app.integrations.weather import WeatherClient
            client = WeatherClient()
            try:
                fc = await client.get_forecast(
                    float(settings.weather_lat), float(settings.weather_lon),
                )
                temp_c = fc.get("temp")
                today_fc = (fc.get("forecast") or [{}])[0]
                hi_c = today_fc.get("high")
                lo_c = today_fc.get("low")
                # Open-Meteo returns Celsius; convert when household
                # is on imperial units. The /api/weather route does
                # the same conversion client-side.
                def _to_unit(v):
                    if v is None:
                        return None
                    return v * 9 / 5 + 32 if settings.weather_units == "imperial" else v
                weather = SplashWeather(
                    available=True,
                    units=settings.weather_units,
                    current_temp=_to_unit(temp_c),
                    high=_to_unit(hi_c),
                    low=_to_unit(lo_c),
                    description=fc.get("description"),
                    icon=fc.get("icon"),
                )
            except Exception:
                # Keep available=True so the section still renders a
                # placeholder; the client will hide it when the temp
                # is None.
                pass
            finally:
                await client.close()

    response.headers["Cache-Control"] = "public, max-age=30"

    return SplashResponse(
        household_id=household.id,
        household_name=household.name,
        clock=SplashClock(
            date=today,
            iso_now=iso_now,
            timezone=settings.timezone,
            time_format=settings.time_format,
        ),
        policy=SplashPolicy(
            splash_mode=settings.splash_mode,
            splash_alternating_ambient_seconds=settings.splash_alternating_ambient_seconds,
            splash_alternating_photo_seconds=settings.splash_alternating_photo_seconds,
            splash_calendar_mode=settings.splash_calendar_mode,
            splash_agenda_max_days=settings.splash_agenda_max_days,
            show_routines=settings.splash_show_routines,
            show_meals=settings.splash_show_meals,
            show_weather=settings.splash_show_weather,
            show_messages=settings.splash_show_messages,
        ),
        days=days,
        routines=routines,
        meals=meals,
        weather=weather,
        messages=messages,
        vacation=vacation,
    )
