"""Pydantic v2 schemas for the Dashboard composite endpoint."""

from __future__ import annotations

import uuid
from datetime import date, datetime

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
    start_time: datetime
    end_time: datetime
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


class DashboardResponse(BaseModel):
    date: date
    profiles: list[ProfileSummary]
    agenda: list[AgendaBucket]
    active_routines: list[dict]
    today_meals: list[MealPlanResponse]
    active_lists: list[ActiveListSummary]
