"""Pydantic schemas for Note endpoints."""

import uuid
import datetime as dt

from pydantic import BaseModel, ConfigDict


class NoteCreate(BaseModel):
    title: str
    body: str = ""
    color: str = "#FBBF24"
    pinned: bool = False
    household_id: uuid.UUID


class NoteUpdate(BaseModel):
    title: str | None = None
    body: str | None = None
    color: str | None = None
    pinned: bool | None = None
    sort_order: int | None = None


class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    household_id: uuid.UUID
    author_profile_id: uuid.UUID
    title: str
    body: str
    color: str
    pinned: bool
    sort_order: int
    created_at: dt.datetime
    updated_at: dt.datetime
