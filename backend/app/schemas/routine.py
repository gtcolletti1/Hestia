import uuid
import datetime as dt

from pydantic import BaseModel, ConfigDict, Field

from app.models.routine import TimeBlock


# ── Routine Steps ────────────────────────────────────────────────────────────


class RoutineStepBase(BaseModel):
    label: str
    icon: str | None = None
    sort_order: int
    points_value: int = 0


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
    start_time: dt.time | None = None
    is_active: bool = True


class RoutineCreate(RoutineBase):
    household_id: uuid.UUID
    profile_id: uuid.UUID | None = None
    steps: list[RoutineStepCreate] = Field(min_length=1)


class RoutineUpdate(BaseModel):
    name: str | None = None
    time_block: TimeBlock | None = None
    days_of_week: list[int] | None = None
    start_time: dt.time | None = None
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
    created_at: dt.datetime
    updated_at: dt.datetime


# ── Completions ──────────────────────────────────────────────────────────────


class RoutineCompletionBase(BaseModel):
    completed_steps: list[str] = []
    is_fully_completed: bool = False


class RoutineCompletionCreate(BaseModel):
    routine_id: uuid.UUID
    profile_id: uuid.UUID
    date: dt.date


class RoutineCompletionResponse(RoutineCompletionBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    routine_id: uuid.UUID
    profile_id: uuid.UUID
    date: dt.date
    completed_at: dt.datetime | None = None
    created_at: dt.datetime


# ── Streak ───────────────────────────────────────────────────────────────────


class StreakInfo(BaseModel):
    current_streak: int
    longest_streak: int
    total_completions: int


# ── Templates ────────────────────────────────────────────────────────────────


class RoutineTemplateStep(BaseModel):
    label: str
    icon: str | None = None
    points_value: int = 0


class RoutineTemplateResponse(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    time_block: TimeBlock
    days_of_week: list[int]
    steps: list[RoutineTemplateStep]
