import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.auth import get_current_profile, get_optional_profile
from app.database import get_db
from app.models.user import Household, Profile, ProfileRole
from app.schemas.profile import (
    HouseholdCreate,
    HouseholdResponse,
    ProfileCreate,
    ProfileResponse,
    ProfileUpdate,
)

router = APIRouter(tags=["profiles"])


# ── Profiles ─────────────────────────────────────────────────────────────────


@router.get("/profiles", response_model=list[ProfileResponse])
async def list_profiles(
    household_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[Profile]:
    result = await db.execute(
        select(Profile).where(Profile.household_id == household_id)
    )
    return list(result.scalars().all())


@router.get("/profiles/{profile_id}", response_model=ProfileResponse)
async def get_profile(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Profile:
    profile = await db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return profile


@router.post("/profiles", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    data: ProfileCreate,
    db: AsyncSession = Depends(get_db),
    actor: Profile | None = Depends(get_optional_profile),
) -> Profile:
    """Create a profile.

    Locked to admins of the same household, with one bootstrap exception:
    when the target household has zero profiles yet (initial setup wizard),
    an unauthenticated request is allowed so the very first admin can be
    created. Subsequent profiles always require an authenticated admin.
    """
    household = await db.get(Household, data.household_id)
    if not household:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Household not found")

    existing_count = (
        await db.execute(
            select(func.count(Profile.id)).where(Profile.household_id == household.id)
        )
    ).scalar_one()

    is_bootstrap = existing_count == 0

    if not is_bootstrap:
        if actor is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        if actor.household_id != household.id or actor.role != ProfileRole.admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only an admin of this household can add profiles",
            )

    if is_bootstrap and data.role != ProfileRole.admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The first profile in a household must be an admin",
        )

    profile = Profile(**data.model_dump())
    db.add(profile)
    await db.flush()
    await db.refresh(profile)
    return profile


@router.put("/profiles/{profile_id}", response_model=ProfileResponse)
async def update_profile(
    profile_id: uuid.UUID,
    data: ProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> Profile:
    profile = await db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    if profile.household_id != current_profile.household_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    is_self = profile.id == current_profile.id
    is_admin = current_profile.role == ProfileRole.admin
    if not (is_self or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own profile",
        )

    updates = data.model_dump(exclude_unset=True)
    # Privilege guards: only admins may change role or activation status,
    # and an admin may not demote the only remaining admin in the household.
    if "role" in updates and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an admin can change profile roles",
        )
    if "is_active" in updates and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an admin can deactivate profiles",
        )
    if (
        ("role" in updates and updates["role"] != ProfileRole.admin)
        or ("is_active" in updates and not updates["is_active"])
    ) and profile.role == ProfileRole.admin:
        admin_count = (
            await db.execute(
                select(func.count(Profile.id)).where(
                    Profile.household_id == profile.household_id,
                    Profile.role == ProfileRole.admin,
                    Profile.is_active.is_(True),
                )
            )
        ).scalar_one()
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last admin",
            )

    for field, value in updates.items():
        setattr(profile, field, value)

    await db.flush()
    await db.refresh(profile)
    return profile


@router.delete("/profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> None:
    profile = await db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    if profile.household_id != current_profile.household_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if current_profile.role != ProfileRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an admin can delete profiles",
        )
    if profile.role == ProfileRole.admin:
        admin_count = (
            await db.execute(
                select(func.count(Profile.id)).where(
                    Profile.household_id == profile.household_id,
                    Profile.role == ProfileRole.admin,
                    Profile.is_active.is_(True),
                )
            )
        ).scalar_one()
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the last admin",
            )
    await db.delete(profile)
    await db.flush()


# ── Households ───────────────────────────────────────────────────────────────


@router.post("/households", response_model=HouseholdResponse, status_code=status.HTTP_201_CREATED)
async def create_household(
    data: HouseholdCreate,
    db: AsyncSession = Depends(get_db),
    actor: Profile | None = Depends(get_optional_profile),
) -> Household:
    """Create a new household.

    Permitted unauthenticated only when no households exist (initial install
    bootstrap). Otherwise an authenticated admin is required.
    """
    existing_count = (
        await db.execute(select(func.count(Household.id)))
    ).scalar_one()
    if existing_count > 0:
        if actor is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        if actor.role != ProfileRole.admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can create households",
            )
    household = Household(**data.model_dump())
    db.add(household)
    await db.flush()
    await db.refresh(household, attribute_names=["profiles"])
    return household


@router.get("/households/{household_id}", response_model=HouseholdResponse)
async def get_household(
    household_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Household:
    result = await db.execute(
        select(Household)
        .options(selectinload(Household.profiles))
        .where(Household.id == household_id)
    )
    household = result.scalar_one_or_none()
    if not household:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Household not found")
    return household
