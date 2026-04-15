"""API routes for family message board notes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_profile
from app.database import get_db
from app.models.note import Note
from app.models.user import Profile
from app.schemas.note import NoteCreate, NoteResponse, NoteUpdate

router = APIRouter(tags=["notes"])


@router.get("/notes", response_model=list[NoteResponse])
async def list_notes(
    household_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> list[Note]:
    if current_profile.household_id != household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    result = await db.execute(
        select(Note)
        .where(Note.household_id == household_id)
        .order_by(Note.pinned.desc(), Note.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/notes", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    data: NoteCreate,
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> Note:
    if current_profile.household_id != data.household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    note = Note(
        **data.model_dump(),
        author_profile_id=current_profile.id,
    )
    db.add(note)
    await db.flush()
    await db.refresh(note)
    return note


@router.put("/notes/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: uuid.UUID,
    data: NoteUpdate,
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> Note:
    note = await db.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if note.household_id != current_profile.household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(note, field, value)
    await db.flush()
    await db.refresh(note)
    return note


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> None:
    note = await db.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if note.household_id != current_profile.household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    await db.delete(note)
    await db.flush()
