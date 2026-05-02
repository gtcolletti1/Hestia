import uuid
import datetime as dt

from pydantic import BaseModel, ConfigDict

from app.models.list import ListCategory


# ── List Items ───────────────────────────────────────────────────────────────


class ListItemBase(BaseModel):
    text: str
    is_checked: bool = False
    sort_order: int = 0
    due_date: dt.date | None = None


class ListItemCreate(ListItemBase):
    assigned_profile_id: uuid.UUID | None = None


class ListItemUpdate(BaseModel):
    text: str | None = None
    is_checked: bool | None = None
    sort_order: int | None = None
    due_date: dt.date | None = None
    assigned_profile_id: uuid.UUID | None = None


class ListItemResponse(ListItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    list_id: uuid.UUID
    assigned_profile_id: uuid.UUID | None = None
    created_at: dt.datetime
    updated_at: dt.datetime


# ── Task Lists ───────────────────────────────────────────────────────────────


class TaskListBase(BaseModel):
    name: str
    category: ListCategory = ListCategory.other
    icon: str | None = None


class TaskListCreate(TaskListBase):
    household_id: uuid.UUID


class TaskListUpdate(BaseModel):
    name: str | None = None
    category: ListCategory | None = None
    icon: str | None = None
    is_archived: bool | None = None
    sort_order: int | None = None


class TaskListResponse(TaskListBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    household_id: uuid.UUID
    sort_order: int
    is_archived: bool
    items: list[ListItemResponse] = []
    item_count: int = 0
    checked_count: int = 0
    created_at: dt.datetime
    updated_at: dt.datetime


# ── Reorder payload ──────────────────────────────────────────────────────────


class ReorderPayload(BaseModel):
    item_ids: list[uuid.UUID]
