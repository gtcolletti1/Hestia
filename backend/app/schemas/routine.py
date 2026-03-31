from __future__ import annotations
import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict

from app.models.routine import TimeBlock


# ── Routine Steps ────────────────────────────────────────────────────────────


class RoutineStepBase(BaseModel):
    label: str
    icon: str | None = None
    sort_order: int


class RoutineStepCreate(RoutineStepBase):
    pass


class RoutineStepResponse(RoutineStepBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID


# ── Routines ─────────────────────────────────────────────────────────────────


class RoutineBase(BaseModel):
    name: str
    time_block: TimeBlock
    days_of_week: list[int]
    start_time: time | None = None
    is_active: bool = True


class RoutineCreate(RoutineBase):
    household_id: uuid.UUID
    profile_id: uuid.UUID | None = None
    steps: list[RoutineStepCreate] = []


class RoutineUpdate(BaseModel):
    name: str | None = None
    time_block: TimeBlock | None = None
    days_of_week: list[int] | None = None
    start_time: time | None = None
    is_active: bool | None = None
    sort_order: int | None = None
    profile_id: uuid.UUID | None = None
    steps: list[RoutineStepCreate] | None = None


class RoutineResponse(RoutineBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    household_id: uuid.UUID
    profile_id: uuid.UUID | None = None
    sort_order: int
    steps: list[RoutineStepResponse] = []
    created_at: datetime
    updated_at: datetime


# ── Completions ──────────────────────────────────────────────────────────────


class RoutineCompletionBase(BaseModel):
    completed_steps: list[str] = []
    is_fully_completed: bool = False


class RoutineCompletionCreate(BaseModel):
    routine_id: uuid.UUID
    profile_id: uuid.UUID
    date: date


class RoutineCompletionResponse(RoutineCompletionBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    routine_id: uuid.UUID
    profile_id: uuid.UUID
    date: date
    completed_at: datetime | None = None
    created_at: datetime


# ── Streak ───────────────────────────────────────────────────────────────────


class StreakInfo(BaseModel):
    current_streak: int
    longest_streak: int
    total_completions: int
