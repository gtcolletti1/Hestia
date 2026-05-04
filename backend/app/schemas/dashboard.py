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


class DashboardResponse(BaseModel):
    date: dt.date
    profiles: list[ProfileSummary]
    agenda: list[AgendaBucket]
    active_routines: list[dict]
    today_meals: list[MealPlanResponse]
    active_lists: list[ActiveListSummary]
    vacation: VacationStatus | None = None
