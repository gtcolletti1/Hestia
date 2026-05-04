"""Pydantic v2 schemas for the public Splash endpoint (PRD §2.12)."""
from __future__ import annotations

import datetime as dt
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict


class SplashClock(BaseModel):
    date: dt.date
    iso_now: dt.datetime
    timezone: str  # IANA name actually applied
    time_format: Literal["12h", "24h"]


class SplashEvent(BaseModel):
    """A single agenda item on the splash.

    When the calendar mode is ``busy_only`` the server replaces ``title``
    with ``"Busy"`` and clears ``location``. The fields are still typed
    the same so the client renders one component for both modes; what
    differs is the *content*, never the *shape*.
    """
    id: uuid.UUID
    title: str
    start_time: dt.datetime
    end_time: dt.datetime
    color: str | None = None
    profile_color: str | None = None
    profile_name: str | None = None
    location: str | None = None
    all_day: bool = False


class SplashDay(BaseModel):
    date: dt.date
    label: str  # "Today", "Tomorrow", or weekday name like "Friday"
    events: list[SplashEvent]


class SplashRoutineAssignee(BaseModel):
    id: uuid.UUID | None = None
    name: str  # "Household" when no profile is assigned
    color: str | None = None
    avatar_url: str | None = None


class SplashRoutine(BaseModel):
    id: uuid.UUID
    name: str
    time_block: str
    step_count: int
    streak_days: int
    assignee: SplashRoutineAssignee


class SplashMeal(BaseModel):
    id: uuid.UUID
    meal_type: str
    title: str


class SplashWeather(BaseModel):
    """Whatever subset of weather we surface on the splash; the splash
    client treats this as opaque display data.
    """
    available: bool = False
    units: str | None = None
    current_temp: float | None = None
    high: float | None = None
    low: float | None = None
    description: str | None = None
    icon: str | None = None


class SplashMessage(BaseModel):
    id: uuid.UUID
    title: str
    body: str
    pinned: bool
    color: str | None = None
    author_name: str | None = None
    created_at: dt.datetime


class SplashPolicy(BaseModel):
    """Echoes the policy that produced this response so the client can
    render the right empty states (e.g., 'agenda hidden by admin') without
    re-fetching settings.
    """
    splash_mode: str
    splash_alternating_ambient_seconds: int
    splash_alternating_photo_seconds: int
    splash_calendar_mode: str
    splash_agenda_max_days: int
    show_routines: bool
    show_meals: bool
    show_weather: bool
    show_messages: bool


class SplashVacation(BaseModel):
    """Mirrors VacationStatus from the dashboard schema; included so
    the unauthenticated splash can show a 🏝 banner without leaking the
    list of suppressed routines."""

    active: bool
    reason: str | None = None
    end_date: dt.date | None = None


class SplashResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    household_id: uuid.UUID
    household_name: str
    clock: SplashClock
    policy: SplashPolicy
    # All sections below are optional. A null/missing field means the
    # admin policy hides this section entirely; a present-but-empty list
    # means the section is enabled but has no content right now.
    days: list[SplashDay] | None = None  # None when calendar_mode == "hidden"
    routines: list[SplashRoutine] | None = None
    meals: list[SplashMeal] | None = None
    weather: SplashWeather | None = None
    messages: list[SplashMessage] | None = None
    vacation: SplashVacation | None = None
