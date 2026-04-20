"""API routes for Meal Plans."""


import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_profile
from app.database import get_db
from app.models.meal import MealPlan
from app.models.user import Profile
from app.schemas.meal import (
    DayMeals,
    MealPlanCreate,
    MealPlanResponse,
    MealPlanUpdate,
    WeeklyMealView,
)

router = APIRouter(tags=["meals"])


@router.get("/meals", response_model=list[MealPlanResponse])
async def list_meals(
    household_id: uuid.UUID,
    date: date | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> list[MealPlanResponse]:
    """Return meals for a single day or a date range."""
    if current_profile.household_id != household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    stmt = select(MealPlan).where(MealPlan.household_id == household_id)

    if date is not None:
        stmt = stmt.where(MealPlan.date == date)
    else:
        if start_date is not None:
            stmt = stmt.where(MealPlan.date >= start_date)
        if end_date is not None:
            stmt = stmt.where(MealPlan.date <= end_date)

    stmt = stmt.order_by(MealPlan.date, MealPlan.meal_type)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/meals/week", response_model=WeeklyMealView)
async def get_weekly_meals(
    household_id: uuid.UUID,
    week_start: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> WeeklyMealView:
    """Return a structured weekly meal view (7 days starting from week_start)."""
    if current_profile.household_id != household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    week_end = week_start + timedelta(days=6)

    stmt = (
        select(MealPlan)
        .where(
            MealPlan.household_id == household_id,
            MealPlan.date >= week_start,
            MealPlan.date <= week_end,
        )
        .order_by(MealPlan.date, MealPlan.meal_type)
    )
    result = await db.execute(stmt)
    meals = result.scalars().all()

    meals_by_date: dict[date, list] = {}
    for m in meals:
        meals_by_date.setdefault(m.date, []).append(m)

    days = [
        DayMeals(
            date=week_start + timedelta(days=i),
            meals=meals_by_date.get(week_start + timedelta(days=i), []),
        )
        for i in range(7)
    ]

    return WeeklyMealView(week_start=week_start, days=days)


@router.get("/meals/{meal_id}", response_model=MealPlanResponse)
async def get_meal(
    meal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> MealPlanResponse:
    """Get a single meal plan by id."""
    result = await db.execute(select(MealPlan).where(MealPlan.id == meal_id))
    meal = result.scalar_one_or_none()
    if meal is None:
        raise HTTPException(status_code=404, detail="Meal plan not found")
    if meal.household_id != current_profile.household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return meal


@router.post("/meals", response_model=MealPlanResponse, status_code=201)
async def create_meal(
    payload: MealPlanCreate,
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> MealPlanResponse:
    """Create a new meal plan."""
    if current_profile.household_id != payload.household_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Enforce one meal per (household, date, meal_type)
    existing = await db.execute(
        select(MealPlan).where(
            MealPlan.household_id == payload.household_id,
            MealPlan.date == payload.date,
            MealPlan.meal_type == payload.meal_type,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"A {payload.meal_type.value} meal already exists for {payload.date}. Edit or delete it first.",
        )

    meal = MealPlan(**payload.model_dump())
    db.add(meal)
    await db.flush()
    await db.refresh(meal)
    return meal


@router.put("/meals/{meal_id}", response_model=MealPlanResponse)
async def update_meal(
    meal_id: uuid.UUID,
    payload: MealPlanUpdate,
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> MealPlanResponse:
    """Update an existing meal plan."""
    result = await db.execute(select(MealPlan).where(MealPlan.id == meal_id))
    meal = result.scalar_one_or_none()
    if meal is None:
        raise HTTPException(status_code=404, detail="Meal plan not found")
    if meal.household_id != current_profile.household_id:
        raise HTTPException(status_code=403, detail="Access denied")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(meal, field, value)

    await db.flush()
    await db.refresh(meal)
    return meal


@router.delete("/meals/{meal_id}", status_code=204)
async def delete_meal(
    meal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> None:
    """Delete a meal plan."""
    result = await db.execute(select(MealPlan).where(MealPlan.id == meal_id))
    meal = result.scalar_one_or_none()
    if meal is None:
        raise HTTPException(status_code=404, detail="Meal plan not found")
    if meal.household_id != current_profile.household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    await db.delete(meal)
    await db.flush()
