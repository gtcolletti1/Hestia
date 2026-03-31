"""Pydantic v2 schemas for Meal Plans."""

import datetime as dt
import uuid

from pydantic import BaseModel, ConfigDict

from app.models.meal import MealType


class MealPlanBase(BaseModel):
    date: dt.date
    meal_type: MealType
    title: str
    description: str | None = None
    recipe_url: str | None = None


class MealPlanCreate(MealPlanBase):
    household_id: uuid.UUID
    assigned_profile_id: uuid.UUID | None = None


class MealPlanUpdate(BaseModel):
    date: dt.date | None = None
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
    created_at: dt.datetime
    updated_at: dt.datetime


class DayMeals(BaseModel):
    date: dt.date
    meals: list[MealPlanResponse]


class WeeklyMealView(BaseModel):
    week_start: dt.date
    days: list[DayMeals]
