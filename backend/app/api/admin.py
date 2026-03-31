"""API routes for Admin / Household settings."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import Household
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
) -> HouseholdSettings:
    """Return current household settings."""
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
) -> HouseholdSettings:
    """Update household settings (partial update)."""
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
) -> HouseholdSettings:
    """Enable or disable a single module."""
    valid_modules = {"calendar", "routines", "lists", "meals"}
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
