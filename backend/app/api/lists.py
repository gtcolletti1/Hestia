from __future__ import annotations
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.list import ListCategory, ListItem, TaskList
from app.schemas.list import (
    ListItemCreate,
    ListItemResponse,
    ListItemUpdate,
    ReorderPayload,
    TaskListCreate,
    TaskListResponse,
    TaskListUpdate,
)

router = APIRouter(tags=["lists"])


def _enrich(task_list: TaskList) -> TaskList:
    """Attach computed item_count and checked_count to the ORM object."""
    task_list.item_count = len(task_list.items)  # type: ignore[attr-defined]
    task_list.checked_count = sum(1 for i in task_list.items if i.is_checked)  # type: ignore[attr-defined]
    return task_list


# ── List task lists ──────────────────────────────────────────────────────────


@router.get("/lists", response_model=list[TaskListResponse])
async def list_task_lists(
    household_id: uuid.UUID = Query(...),
    category: ListCategory | None = Query(None),
    include_archived: bool = Query(False),
    db: AsyncSession = Depends(get_db),
) -> list[TaskList]:
    stmt = (
        select(TaskList)
        .options(selectinload(TaskList.items))
        .where(TaskList.household_id == household_id)
        .order_by(TaskList.sort_order)
    )
    if not include_archived:
        stmt = stmt.where(TaskList.is_archived.is_(False))
    if category is not None:
        stmt = stmt.where(TaskList.category == category)
    result = await db.execute(stmt)
    return [_enrich(tl) for tl in result.scalars().all()]


# ── Get task list ────────────────────────────────────────────────────────────


@router.get("/lists/{list_id}", response_model=TaskListResponse)
async def get_task_list(
    list_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> TaskList:
    stmt = (
        select(TaskList)
        .options(selectinload(TaskList.items))
        .where(TaskList.id == list_id)
    )
    result = await db.execute(stmt)
    task_list = result.scalar_one_or_none()
    if task_list is None:
        raise HTTPException(status_code=404, detail="List not found")
    return _enrich(task_list)


# ── Create task list ─────────────────────────────────────────────────────────


@router.post("/lists", response_model=TaskListResponse, status_code=201)
async def create_task_list(
    payload: TaskListCreate,
    db: AsyncSession = Depends(get_db),
) -> TaskList:
    task_list = TaskList(
        household_id=payload.household_id,
        name=payload.name,
        category=payload.category,
        icon=payload.icon,
    )
    db.add(task_list)
    await db.flush()

    stmt = (
        select(TaskList)
        .options(selectinload(TaskList.items))
        .where(TaskList.id == task_list.id)
    )
    result = await db.execute(stmt)
    return _enrich(result.scalar_one())


# ── Update task list ─────────────────────────────────────────────────────────


@router.put("/lists/{list_id}", response_model=TaskListResponse)
async def update_task_list(
    list_id: uuid.UUID,
    payload: TaskListUpdate,
    db: AsyncSession = Depends(get_db),
) -> TaskList:
    stmt = (
        select(TaskList)
        .options(selectinload(TaskList.items))
        .where(TaskList.id == list_id)
    )
    result = await db.execute(stmt)
    task_list = result.scalar_one_or_none()
    if task_list is None:
        raise HTTPException(status_code=404, detail="List not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task_list, field, value)

    await db.flush()
    await db.refresh(task_list)
    return _enrich(task_list)


# ── Delete task list ─────────────────────────────────────────────────────────


@router.delete("/lists/{list_id}", status_code=204)
async def delete_task_list(
    list_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    stmt = select(TaskList).where(TaskList.id == list_id)
    result = await db.execute(stmt)
    task_list = result.scalar_one_or_none()
    if task_list is None:
        raise HTTPException(status_code=404, detail="List not found")
    await db.delete(task_list)


# ── Add item to list ────────────────────────────────────────────────────────


@router.post("/lists/{list_id}/items", response_model=ListItemResponse, status_code=201)
async def add_item(
    list_id: uuid.UUID,
    payload: ListItemCreate,
    db: AsyncSession = Depends(get_db),
) -> ListItem:
    # Verify list exists
    stmt = select(TaskList).where(TaskList.id == list_id)
    result = await db.execute(stmt)
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="List not found")

    item = ListItem(
        list_id=list_id,
        text=payload.text,
        is_checked=payload.is_checked,
        sort_order=payload.sort_order,
        due_date=payload.due_date,
        assigned_profile_id=payload.assigned_profile_id,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


# ── Update item ──────────────────────────────────────────────────────────────


@router.put("/lists/{list_id}/items/{item_id}", response_model=ListItemResponse)
async def update_item(
    list_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: ListItemUpdate,
    db: AsyncSession = Depends(get_db),
) -> ListItem:
    stmt = select(ListItem).where(ListItem.id == item_id, ListItem.list_id == list_id)
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    await db.flush()
    await db.refresh(item)
    return item


# ── Delete item ──────────────────────────────────────────────────────────────


@router.delete("/lists/{list_id}/items/{item_id}", status_code=204)
async def delete_item(
    list_id: uuid.UUID,
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    stmt = select(ListItem).where(ListItem.id == item_id, ListItem.list_id == list_id)
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    await db.delete(item)


# ── Toggle item checked ─────────────────────────────────────────────────────


@router.patch("/lists/{list_id}/items/{item_id}/toggle", response_model=ListItemResponse)
async def toggle_item(
    list_id: uuid.UUID,
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ListItem:
    stmt = select(ListItem).where(ListItem.id == item_id, ListItem.list_id == list_id)
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    item.is_checked = not item.is_checked
    await db.flush()
    await db.refresh(item)
    return item


# ── Reorder items ────────────────────────────────────────────────────────────


@router.put("/lists/{list_id}/reorder", response_model=list[ListItemResponse])
async def reorder_items(
    list_id: uuid.UUID,
    payload: ReorderPayload,
    db: AsyncSession = Depends(get_db),
) -> list[ListItem]:
    # Verify list exists
    stmt = select(TaskList).where(TaskList.id == list_id)
    result = await db.execute(stmt)
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="List not found")

    # Fetch all items for this list
    stmt = select(ListItem).where(ListItem.list_id == list_id)
    result = await db.execute(stmt)
    items_by_id = {item.id: item for item in result.scalars().all()}

    for idx, item_id in enumerate(payload.item_ids):
        item = items_by_id.get(item_id)
        if item is None:
            raise HTTPException(
                status_code=400,
                detail=f"Item {item_id} not found in list {list_id}",
            )
        item.sort_order = idx

    await db.flush()

    # Refresh items so lazy-loaded columns (updated_at) are available
    for item in items_by_id.values():
        await db.refresh(item)

    # Return in new order
    return [items_by_id[item_id] for item_id in payload.item_ids if item_id in items_by_id]
