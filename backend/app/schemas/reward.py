"""Pydantic schemas for the rewards system."""

import uuid
import datetime as dt

from pydantic import BaseModel, ConfigDict


class RewardCreate(BaseModel):
    title: str
    description: str | None = None
    points_cost: int = 10
    icon: str = "🎁"
    household_id: uuid.UUID


class RewardUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    points_cost: int | None = None
    icon: str | None = None
    is_active: bool | None = None


class RewardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    household_id: uuid.UUID
    title: str
    description: str | None
    points_cost: int
    icon: str | None
    is_active: int
    created_at: dt.datetime


class PointBalanceResponse(BaseModel):
    profile_id: uuid.UUID
    total_points: int


class LeaderboardEntry(BaseModel):
    profile_id: uuid.UUID
    display_name: str
    avatar_url: str | None
    total_points: int


class RedeemRequest(BaseModel):
    reward_id: uuid.UUID
    profile_id: uuid.UUID
    household_id: uuid.UUID


class PointLedgerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    profile_id: uuid.UUID
    points: int
    reason: str
    created_at: dt.datetime
