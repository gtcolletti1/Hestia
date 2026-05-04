"""Schemas for school closures (snow days, in-service days, etc.)."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class SchoolClosureBase(BaseModel):
    date: date
    reason: str | None = None


class SchoolClosureCreate(SchoolClosureBase):
    household_id: uuid.UUID


class SchoolClosureResponse(SchoolClosureBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    household_id: uuid.UUID
    created_by_profile_id: uuid.UUID | None
    created_at: datetime
