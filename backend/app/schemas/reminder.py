"""Pydantic schemas for Reminder / Notification endpoints."""

import uuid
import datetime as dt

from pydantic import BaseModel, ConfigDict


class ReminderCreate(BaseModel):
    event_id: uuid.UUID
    minutes_before: int = 15
    household_id: uuid.UUID


class ReminderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_id: uuid.UUID
    household_id: uuid.UUID
    minutes_before: int
    is_fired: bool
    fire_at: dt.datetime
    created_at: dt.datetime


class UpcomingNotification(BaseModel):
    """Notification payload returned to the frontend."""
    reminder_id: uuid.UUID
    event_id: uuid.UUID
    event_title: str
    event_start: dt.datetime
    minutes_before: int
    fire_at: dt.datetime


class InboxEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    household_id: uuid.UUID
    profile_id: uuid.UUID | None
    kind: str
    title: str
    body: str | None
    link_url: str | None
    created_at: dt.datetime
    read_at: dt.datetime | None


class InboxUnreadCount(BaseModel):
    unread: int
