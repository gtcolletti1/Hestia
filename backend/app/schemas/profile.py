from __future__ import annotations
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.user import ProfileRole


# ── Profile schemas ──────────────────────────────────────────────────────────


class ProfileBase(BaseModel):
    name: str
    color: str
    avatar_url: str | None = None
    role: ProfileRole = ProfileRole.standard


class ProfileCreate(ProfileBase):
    household_id: uuid.UUID


class ProfileUpdate(BaseModel):
    name: str | None = None
    color: str | None = None
    avatar_url: str | None = None
    role: ProfileRole | None = None
    is_active: bool | None = None


class ProfileResponse(ProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    household_id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ── Household schemas ────────────────────────────────────────────────────────


class HouseholdBase(BaseModel):
    name: str


class HouseholdCreate(HouseholdBase):
    pass


class HouseholdResponse(HouseholdBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    profiles: list[ProfileResponse] = []
