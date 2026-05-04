"""Pydantic v2 schemas for the Dashboard composite endpoint."""


import uuid
import datetime as dt

from pydantic import BaseModel, ConfigDict

from app.schemas.meal import MealPlanResponse


class ProfileSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    color: str
    avatar_url: str | None = None


class EventSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    start_time: dt.datetime
    end_time: dt.datetime
    color: str | None = None
    profile_name: str | None = None
    location: str | None = None


class AgendaBucket(BaseModel):
    bucket: str  # "morning" | "afternoon" | "evening"
    events: list[EventSummary]


class ActiveListSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    item_count: int
    checked_count: int


class VacationStatus(BaseModel):
    """Set on /api/dashboard and /api/splash when an active household-wide
    pause override (kind=pause, routine_id=null) covers today, so the
    home/splash views can show a 🏝 banner explaining why pausable
    routines are missing."""

    active: bool
    reason: str | None = None
    end_date: dt.date | None = None  # None = indefinite


class SchoolDayStatus(BaseModel):
    """Tells the home/dashboard whether today is a school day for the
    household. ``reason`` is ``None`` on weekends and on regular school
    days; populated for US federal holidays (e.g. ``"Martin Luther King
    Jr. Day"``) and admin-marked closures (snow days, in-service days)
    so the home view can show a short banner explaining why
    ``school_day_only`` routine steps are absent."""

    is_school_day: bool
    reason: str | None = None
    hidden_step_count: int = 0


class DashboardResponse(BaseModel):
    date: dt.date
    profiles: list[ProfileSummary]
    agenda: list[AgendaBucket]
    active_routines: list[dict]
    today_meals: list[MealPlanResponse]
    active_lists: list[ActiveListSummary]
    vacation: VacationStatus | None = None
    school_day: SchoolDayStatus | None = None
    routines_all_done: bool = False
