from __future__ import annotations
import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.calendar import CalendarProvider


# ── Event schemas ────────────────────────────────────────────────────────────


class EventBase(BaseModel):
    title: str
    description: str | None = None
    location: str | None = None
    start_time: datetime
    end_time: datetime
    all_day: bool = False
    recurrence_rule: str | None = None
    color: str | None = None
    is_private: bool = False


class EventCreate(EventBase):
    source_calendar_id: uuid.UUID
    profile_id: uuid.UUID | None = None


class EventUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    location: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    all_day: bool | None = None
    recurrence_rule: str | None = None
    color: str | None = None
    is_private: bool | None = None
    source_calendar_id: uuid.UUID | None = None
    profile_id: uuid.UUID | None = None


class EventResponse(EventBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_calendar_id: uuid.UUID
    profile_id: uuid.UUID | None
    external_id: str | None
    created_at: datetime
    updated_at: datetime


# ── SourceCalendar schemas ───────────────────────────────────────────────────


class SourceCalendarBase(BaseModel):
    name: str
    provider: CalendarProvider
    is_read_only: bool = False
    is_visible: bool = True
    color: str | None = None


class SourceCalendarCreate(SourceCalendarBase):
    household_id: uuid.UUID
    profile_id: uuid.UUID | None = None


class SourceCalendarUpdate(BaseModel):
    name: str | None = None
    provider: CalendarProvider | None = None
    is_read_only: bool | None = None
    is_visible: bool | None = None
    color: str | None = None


class SourceCalendarResponse(SourceCalendarBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    household_id: uuid.UUID
    profile_id: uuid.UUID | None
    external_id: str | None
    sync_token: str | None
    last_synced_at: datetime | None
    created_at: datetime
    updated_at: datetime


# ── Query helpers ────────────────────────────────────────────────────────────


class CalendarQuery(BaseModel):
    start_date: date
    end_date: date
    profile_ids: list[uuid.UUID] | None = None
    source_calendar_ids: list[uuid.UUID] | None = None
