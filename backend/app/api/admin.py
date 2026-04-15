"""API routes for Admin / Household settings."""


import uuid
from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_profile, require_admin
from app.database import get_db
from app.models.calendar import CalendarProvider, Event, SourceCalendar
from app.models.list import ListCategory, ListItem, TaskList
from app.models.meal import MealPlan, MealType
from app.models.routine import Routine, RoutineStep, TimeBlock
from app.models.user import Household, Profile, ProfileRole
from app.schemas.admin import (
    HouseholdSettings,
    HouseholdSettingsUpdate,
    ModuleToggle,
    ModulesEnabled,
)

router = APIRouter(tags=["admin"])

# Default settings used when a household has no settings stored yet.
_DEFAULT_SETTINGS = HouseholdSettings(name="").model_dump()


def _load_settings(household: Household) -> HouseholdSettings:
    """Build a HouseholdSettings from the stored JSON, falling back to defaults."""
    stored = household.settings or {}
    merged = {**_DEFAULT_SETTINGS, **stored, "name": household.name}
    return HouseholdSettings(**merged)


@router.get("/admin/settings", response_model=HouseholdSettings)
async def get_settings(
    household_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> HouseholdSettings:
    """Return current household settings."""
    if current_profile.household_id != household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    result = await db.execute(
        select(Household).where(Household.id == household_id)
    )
    household = result.scalar_one_or_none()
    if household is None:
        raise HTTPException(status_code=404, detail="Household not found")

    return _load_settings(household)


@router.put("/admin/settings", response_model=HouseholdSettings)
async def update_settings(
    payload: HouseholdSettingsUpdate,
    household_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(require_admin),
) -> HouseholdSettings:
    """Update household settings (partial update)."""
    if current_profile.household_id != household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    result = await db.execute(
        select(Household).where(Household.id == household_id)
    )
    household = result.scalar_one_or_none()
    if household is None:
        raise HTTPException(status_code=404, detail="Household not found")

    current = _load_settings(household)
    update_data = payload.model_dump(exclude_unset=True)

    # If the household name is being changed, persist it on the model column too.
    if "name" in update_data:
        household.name = update_data.pop("name")

    # Merge remaining fields into the settings JSON.
    settings_dict = current.model_dump()
    settings_dict.update(update_data)
    # Persist modules_enabled as plain dict for JSON serialisation.
    if isinstance(settings_dict.get("modules_enabled"), ModulesEnabled):
        settings_dict["modules_enabled"] = settings_dict["modules_enabled"].model_dump()
    household.settings = settings_dict

    await db.flush()
    await db.refresh(household)
    return _load_settings(household)


@router.patch("/admin/modules", response_model=HouseholdSettings)
async def toggle_module(
    payload: ModuleToggle,
    household_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(require_admin),
) -> HouseholdSettings:
    """Enable or disable a single module."""
    if current_profile.household_id != household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    valid_modules = {"calendar", "routines", "lists", "meals", "weather"}
    if payload.module not in valid_modules:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid module '{payload.module}'. Must be one of {sorted(valid_modules)}.",
        )

    result = await db.execute(
        select(Household).where(Household.id == household_id)
    )
    household = result.scalar_one_or_none()
    if household is None:
        raise HTTPException(status_code=404, detail="Household not found")

    current = _load_settings(household)
    modules = current.modules_enabled.model_dump()
    modules[payload.module] = payload.enabled

    settings_dict = current.model_dump()
    settings_dict["modules_enabled"] = modules
    household.settings = settings_dict

    await db.flush()
    await db.refresh(household)
    return _load_settings(household)


# ── Seed endpoint ────────────────────────────────────────────────────────────


@router.post("/seed")
async def seed_database(db: AsyncSession = Depends(get_db)) -> dict:
    """Populate the database with sample data for testing.

    Returns the household_id.  Refuses to run if any household already exists.
    """
    existing = await db.execute(select(func.count()).select_from(Household))
    if existing.scalar_one() > 0:
        raise HTTPException(
            status_code=409,
            detail="Seed data already exists. Delete all households first.",
        )

    now = datetime.now(timezone.utc)
    today = date.today()

    # ── Household ────────────────────────────────────────────────────────
    household = Household(name="The Family")
    db.add(household)
    await db.flush()

    # ── Profiles ─────────────────────────────────────────────────────────
    mom = Profile(
        household_id=household.id, name="Mom", color="#EC4899", role=ProfileRole.admin
    )
    dad = Profile(
        household_id=household.id, name="Dad", color="#3B82F6", role=ProfileRole.admin
    )
    emma = Profile(
        household_id=household.id, name="Emma", color="#8B5CF6", role=ProfileRole.kid
    )
    jack = Profile(
        household_id=household.id, name="Jack", color="#22C55E", role=ProfileRole.kid
    )
    db.add_all([mom, dad, emma, jack])
    await db.flush()

    # ── Source calendar ──────────────────────────────────────────────────
    cal = SourceCalendar(
        household_id=household.id,
        provider=CalendarProvider.local,
        name="Family Calendar",
    )
    db.add(cal)
    await db.flush()

    # ── Events (next 2 weeks) ────────────────────────────────────────────
    def _dt(day_offset: int, hour: int, minute: int = 0) -> datetime:
        return datetime(
            today.year, today.month, today.day,
            hour, minute, tzinfo=timezone.utc,
        ) + timedelta(days=day_offset)

    events_data = [
        # (title, description, location, day_offset, start_h, start_m, end_h, end_m, profile, color)
        ("School drop-off", "Drop kids at school", "Lincoln Elementary", 1, 8, 0, 8, 30, mom, "#F59E0B"),
        ("Soccer practice", "Bring cleats and water", "City Park Field 3", 1, 16, 0, 17, 30, emma, "#8B5CF6"),
        ("Dentist – Emma", "Regular checkup", "Smile Dental", 2, 10, 0, 11, 0, emma, "#EF4444"),
        ("Grocery run", "Weekly groceries", "Trader Joe's", 3, 11, 0, 12, 0, mom, "#EC4899"),
        ("Date night", "Dinner reservation", "Chez Laurent", 4, 19, 0, 22, 0, dad, "#3B82F6"),
        ("Soccer practice", "Bring cleats and water", "City Park Field 3", 5, 16, 0, 17, 30, emma, "#8B5CF6"),
        ("Birthday party – Lily", "Bring gift", "Lily's house", 6, 14, 0, 16, 0, jack, "#22C55E"),
        ("Piano lesson", "Practice scales beforehand", "Ms. Chen's Studio", 7, 15, 0, 15, 45, emma, "#8B5CF6"),
        ("School drop-off", "Drop kids at school", "Lincoln Elementary", 8, 8, 0, 8, 30, dad, "#3B82F6"),
        ("Science fair prep", "Finish volcano project", "Home", 9, 10, 0, 12, 0, jack, "#22C55E"),
        ("Family movie night", "Pick a movie!", "Home", 10, 19, 0, 21, 30, None, "#F59E0B"),
        ("PTA meeting", "Quarterly meeting", "Lincoln Elementary", 11, 18, 0, 19, 0, mom, "#EC4899"),
        ("Soccer game", "Home game – bring snacks", "City Park Field 1", 12, 9, 0, 10, 30, emma, "#8B5CF6"),
    ]

    for title, desc, loc, doff, sh, sm, eh, em, prof, clr in events_data:
        db.add(Event(
            source_calendar_id=cal.id,
            profile_id=prof.id if prof else None,
            title=title,
            description=desc,
            location=loc,
            start_time=_dt(doff, sh, sm),
            end_time=_dt(doff, eh, em),
            color=clr,
        ))

    # ── Routines ─────────────────────────────────────────────────────────
    weekdays = [0, 1, 2, 3, 4]
    every_day = [0, 1, 2, 3, 4, 5, 6]

    routines_spec = [
        ("Morning Routine", TimeBlock.morning, weekdays, time(7, 0), [
            ("Wake up", "⏰"),
            ("Brush teeth", "🪥"),
            ("Get dressed", "👕"),
            ("Eat breakfast", "🥣"),
            ("Pack backpack", "🎒"),
        ]),
        ("Bedtime Routine", TimeBlock.bedtime, every_day, time(20, 0), [
            ("Bath time", "🛁"),
            ("Brush teeth", "🪥"),
            ("Put on pajamas", "🌙"),
            ("Story time", "📖"),
            ("Lights out", "💤"),
        ]),
        ("After School", TimeBlock.afternoon, weekdays, time(15, 30), [
            ("Snack", "🍎"),
            ("Homework", "📝"),
            ("Free play", "🎮"),
        ]),
    ]

    for rname, tblock, days, stime, steps in routines_spec:
        routine = Routine(
            household_id=household.id,
            name=rname,
            time_block=tblock,
            days_of_week=days,
            start_time=stime,
        )
        db.add(routine)
        await db.flush()
        for idx, (label, icon) in enumerate(steps):
            db.add(RoutineStep(
                routine_id=routine.id,
                label=label,
                icon=icon,
                sort_order=idx,
            ))

    # ── Lists ────────────────────────────────────────────────────────────
    lists_spec = [
        ("Groceries", ListCategory.grocery, "🛒", [
            "Milk", "Eggs", "Bread", "Bananas", "Chicken", "Pasta", "Tomato sauce", "Cheese",
        ]),
        ("Weekend To-Do", ListCategory.todo, "✅", [
            "Mow lawn", "Clean garage", "Fix fence", "Wash car",
        ]),
        ("School Supplies", ListCategory.school, "📚", [
            "Notebooks", "Pencils", "Glue sticks", "Scissors",
        ]),
    ]

    for lname, cat, icon, items in lists_spec:
        tl = TaskList(
            household_id=household.id,
            name=lname,
            category=cat,
            icon=icon,
        )
        db.add(tl)
        await db.flush()
        for idx, text in enumerate(items):
            db.add(ListItem(list_id=tl.id, text=text, sort_order=idx))

    # ── Meal plans (current week, Mon–Sun) ───────────────────────────────
    weekday_offset = today.weekday()  # 0=Mon
    monday = today - timedelta(days=weekday_offset)

    weekly_meals = [
        # (day_offset, meal_type, title, description)
        (0, MealType.breakfast, "Oatmeal & fruit", "Steel-cut oats with blueberries"),
        (0, MealType.lunch, "Turkey sandwiches", "Whole wheat with veggies"),
        (0, MealType.dinner, "Spaghetti Bolognese", "Classic family recipe"),
        (1, MealType.breakfast, "Scrambled eggs & toast", None),
        (1, MealType.lunch, "Chicken Caesar wraps", None),
        (1, MealType.dinner, "Tacos", "Ground beef with all the fixings"),
        (2, MealType.breakfast, "Pancakes", "With maple syrup"),
        (2, MealType.lunch, "Tomato soup & grilled cheese", None),
        (2, MealType.dinner, "Stir-fry chicken & veggies", "Serve over rice"),
        (3, MealType.breakfast, "Yogurt parfait", "Greek yogurt with granola"),
        (3, MealType.lunch, "PB&J + apple slices", None),
        (3, MealType.dinner, "Baked salmon", "With roasted asparagus"),
        (4, MealType.breakfast, "Cereal & milk", None),
        (4, MealType.lunch, "Leftover stir-fry", None),
        (4, MealType.dinner, "Pizza night", "Homemade with favorite toppings"),
        (5, MealType.breakfast, "French toast", "With powdered sugar"),
        (5, MealType.lunch, "Mac & cheese", "Baked, not boxed"),
        (5, MealType.dinner, "Burgers on the grill", "With sweet potato fries"),
        (6, MealType.breakfast, "Waffles", "Belgian waffles with strawberries"),
        (6, MealType.lunch, "Quesadillas", "Chicken and cheese"),
        (6, MealType.dinner, "Roast chicken", "With mashed potatoes and gravy"),
    ]

    cooks = [mom, dad]
    for idx, (doff, mtype, title, desc) in enumerate(weekly_meals):
        db.add(MealPlan(
            household_id=household.id,
            date=monday + timedelta(days=doff),
            meal_type=mtype,
            title=title,
            description=desc,
            assigned_profile_id=cooks[idx % 2].id,
        ))

    await db.flush()

    return {"household_id": str(household.id), "message": "Seed data created successfully"}
