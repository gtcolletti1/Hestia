"""Pydantic schemas for Photo endpoints."""

import uuid
import datetime as dt

from pydantic import BaseModel, ConfigDict


class PhotoCreate(BaseModel):
    url: str
    caption: str | None = None
    sort_order: int = 0
    household_id: uuid.UUID


class PhotoUpdate(BaseModel):
    caption: str | None = None
    sort_order: int | None = None


class PhotoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    household_id: uuid.UUID
    url: str
    caption: str | None
    sort_order: int
    created_at: dt.datetime
