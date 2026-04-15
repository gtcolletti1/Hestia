"""API routes for Photos (screensaver slideshow)."""

import os
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_profile, require_admin
from app.database import get_db
from app.models.photo import Photo
from app.models.user import Profile
from app.schemas.photo import PhotoCreate, PhotoResponse, PhotoUpdate

router = APIRouter(tags=["photos"])

UPLOAD_DIR = os.environ.get("PHOTO_UPLOAD_DIR", "/app/uploads/photos")
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


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
    # Clean up uploaded file if it's a local upload
    if photo.url.startswith("/api/photos/file/"):
        filename = photo.url.rsplit("/", 1)[-1]
        filepath = os.path.join(UPLOAD_DIR, filename)
        if os.path.isfile(filepath):
            os.remove(filepath)
    await db.delete(photo)
    await db.flush()


@router.post("/photos/upload", response_model=PhotoResponse, status_code=status.HTTP_201_CREATED)
async def upload_photo(
    household_id: str = Form(...),
    caption: str = Form(""),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(require_admin),
) -> Photo:
    hid = uuid.UUID(household_id)
    if current_profile.household_id != hid:
        raise HTTPException(status_code=403, detail="Access denied")
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"File type not allowed. Must be one of: {', '.join(ALLOWED_TYPES)}")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10 MB)")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(contents)

    photo = Photo(
        household_id=hid,
        url=f"/api/photos/file/{filename}",
        caption=caption or None,
    )
    db.add(photo)
    await db.flush()
    await db.refresh(photo)
    return photo


@router.get("/photos/file/{filename}")
async def serve_photo(filename: str) -> FileResponse:
    # Prevent path traversal
    safe_name = os.path.basename(filename)
    filepath = os.path.join(UPLOAD_DIR, safe_name)
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(filepath)
