"""Tests for the sync queue service."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration import SyncAction, SyncStatus
from app.models.user import Household
from app.services.sync_queue import enqueue_change, get_pending_count, process_queue

pytestmark = pytest.mark.asyncio


async def test_enqueue_change(
    db_session: AsyncSession, sample_household: Household
) -> None:
    entity_id = uuid.uuid4()
    item = await enqueue_change(
        db=db_session,
        household_id=sample_household.id,
        entity_type="event",
        entity_id=entity_id,
        action=SyncAction.create,
        payload={"title": "New Event"},
    )
    assert item.id is not None
    assert item.entity_type == "event"
    assert item.entity_id == entity_id
    assert item.action == SyncAction.create
    assert item.status == SyncStatus.pending


async def test_process_queue(
    db_session: AsyncSession, sample_household: Household
) -> None:
    # Enqueue two items
    for i in range(2):
        await enqueue_change(
            db=db_session,
            household_id=sample_household.id,
            entity_type="list_item",
            entity_id=uuid.uuid4(),
            action=SyncAction.update,
        )

    # _push_to_external_service is a no-op stub, so all items should succeed
    processed = await process_queue(db_session, sample_household.id)
    assert processed == 2

    # Nothing pending anymore
    pending = await get_pending_count(db_session, sample_household.id)
    assert pending == 0


async def test_get_pending_count(
    db_session: AsyncSession, sample_household: Household
) -> None:
    # Start from zero
    assert await get_pending_count(db_session, sample_household.id) == 0

    await enqueue_change(
        db=db_session,
        household_id=sample_household.id,
        entity_type="event",
        entity_id=uuid.uuid4(),
        action=SyncAction.delete,
    )
    assert await get_pending_count(db_session, sample_household.id) == 1

    await enqueue_change(
        db=db_session,
        household_id=sample_household.id,
        entity_type="event",
        entity_id=uuid.uuid4(),
        action=SyncAction.create,
    )
    assert await get_pending_count(db_session, sample_household.id) == 2
