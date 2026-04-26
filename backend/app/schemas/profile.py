import uuid
import datetime as dt

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.user import ProfileRole


# ── Profile schemas ──────────────────────────────────────────────────────────


class ProfileBase(BaseModel):
    name: str
    color: str
    avatar_url: str | None = None
    role: ProfileRole = ProfileRole.standard


class ProfileCreate(ProfileBase):
    household_id: uuid.UUID
    pin: str | None = Field(
        default=None,
        description="Optional PIN to set during creation (4-12 digits).",
    )

    @field_validator("pin")
    @classmethod
    def _validate_pin(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        if not (v.isdigit() and 4 <= len(v) <= 12):
            raise ValueError("PIN must be 4-12 digits")
        return v


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
    pin_set: bool = False
    created_at: dt.datetime
    updated_at: dt.datetime


# ── Household schemas ────────────────────────────────────────────────────────


class HouseholdBase(BaseModel):
    name: str


class HouseholdCreate(HouseholdBase):
    pass


class HouseholdResponse(HouseholdBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: dt.datetime
    updated_at: dt.datetime
    profiles: list[ProfileResponse] = []


# ── Setup / discovery schemas ────────────────────────────────────────────────


class HouseholdSummary(BaseModel):
    """Minimal pre-login household info exposed by /api/setup/discover."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class SetupDiscoverResponse(BaseModel):
    setup_required: bool
    households: list[HouseholdSummary]
