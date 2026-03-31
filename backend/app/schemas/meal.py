"""Pydantic v2 schemas for Meal Plans."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.meal import MealType


class MealPlanBase(BaseModel):
    date: date
    meal_type: MealType
    title: str
    description: str | None = None
    recipe_url: str | None = None


class MealPlanCreate(MealPlanBase):
    household_id: uuid.UUID
    assigned_profile_id: uuid.UUID | None = None


class MealPlanUpdate(BaseModel):
    date: date | None = None
    meal_type: MealType | None = None
    title: str | None = None
    description: str | None = None
    recipe_url: str | None = None
    assigned_profile_id: uuid.UUID | None = None


class MealPlanResponse(MealPlanBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    household_id: uuid.UUID
    assigned_profile_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class DayMeals(BaseModel):
    date: date
    meals: list[MealPlanResponse]


class WeeklyMealView(BaseModel):
    week_start: date
    days: list[DayMeals]
