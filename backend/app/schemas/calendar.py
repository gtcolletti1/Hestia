import uuid
import datetime as dt

from pydantic import BaseModel, ConfigDict, model_validator

from app.models.calendar import CalendarProvider


# ── Event schemas ────────────────────────────────────────────────────────────


class EventBase(BaseModel):
    title: str
    description: str | None = None
    location: str | None = None
    start_time: dt.datetime
    end_time: dt.datetime
    all_day: bool = False
    recurrence_rule: str | None = None
    color: str | None = None
    is_private: bool = False


class EventCreate(EventBase):
    source_calendar_id: uuid.UUID
    profile_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def validate_times(self):
        if not self.all_day and self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")
        return self


class EventUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    location: str | None = None
    start_time: dt.datetime | None = None
    end_time: dt.datetime | None = None
    all_day: bool | None = None
    recurrence_rule: str | None = None
    color: str | None = None
    is_private: bool | None = None
    source_calendar_id: uuid.UUID | None = None
    profile_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def validate_times(self):
        if self.start_time is not None and self.end_time is not None:
            if not self.all_day and self.start_time >= self.end_time:
                raise ValueError("start_time must be before end_time")
        return self


class EventResponse(EventBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_calendar_id: uuid.UUID
    profile_id: uuid.UUID | None
    external_id: str | None
    created_at: dt.datetime
    updated_at: dt.datetime


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
    last_synced_at: dt.datetime | None
    created_at: dt.datetime
    updated_at: dt.datetime


# ── Query helpers ────────────────────────────────────────────────────────────


class CalendarQuery(BaseModel):
    start_date: dt.date
    end_date: dt.date
    profile_ids: list[uuid.UUID] | None = None
    source_calendar_ids: list[uuid.UUID] | None = None
