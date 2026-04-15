"""API routes for Photos (screensaver slideshow)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_profile, require_admin
from app.database import get_db
from app.models.photo import Photo
from app.models.user import Profile
from app.schemas.photo import PhotoCreate, PhotoResponse, PhotoUpdate

router = APIRouter(tags=["photos"])


@router.get("/photos", response_model=list[PhotoResponse])
async def list_photos(
    household_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> list[Photo]:
    if current_profile.household_id != household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    result = await db.execute(
        select(Photo)
        .where(Photo.household_id == household_id)
        .order_by(Photo.sort_order, Photo.created_at)
    )
    return list(result.scalars().all())


@router.post("/photos", response_model=PhotoResponse, status_code=status.HTTP_201_CREATED)
async def create_photo(
    data: PhotoCreate,
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(require_admin),
) -> Photo:
    if current_profile.household_id != data.household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    photo = Photo(**data.model_dump())
    db.add(photo)
    await db.flush()
    await db.refresh(photo)
    return photo


@router.put("/photos/{photo_id}", response_model=PhotoResponse)
async def update_photo(
    photo_id: uuid.UUID,
    data: PhotoUpdate,
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(require_admin),
) -> Photo:
    photo = await db.get(Photo, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    if photo.household_id != current_profile.household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(photo, field, value)
    await db.flush()
    await db.refresh(photo)
    return photo


@router.delete("/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo(
    photo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(require_admin),
) -> None:
    photo = await db.get(Photo, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    if photo.household_id != current_profile.household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    await db.delete(photo)
    await db.flush()
