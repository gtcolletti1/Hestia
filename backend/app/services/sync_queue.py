import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration import SyncAction, SyncQueueItem, SyncStatus

logger = logging.getLogger(__name__)

MAX_RETRIES_DEFAULT = 3


async def enqueue_change(
    db: AsyncSession,
    household_id: uuid.UUID,
    entity_type: str,
    entity_id: uuid.UUID,
    action: SyncAction,
    payload: dict | None = None,
) -> SyncQueueItem:
    """Add an item to the sync queue for later processing."""
    item = SyncQueueItem(
        household_id=household_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        payload=payload,
        status=SyncStatus.pending,
    )
    db.add(item)
    await db.flush()
    logger.info("Enqueued sync item %s (%s %s)", item.id, action.value, entity_type)
    return item


async def process_queue(db: AsyncSession, household_id: uuid.UUID) -> int:
    """Process all pending sync queue items for a household.

    Returns the number of items processed successfully.
    """
    result = await db.execute(
        select(SyncQueueItem)
        .where(
            SyncQueueItem.household_id == household_id,
            SyncQueueItem.status == SyncStatus.pending,
        )
        .order_by(SyncQueueItem.created_at.asc())
    )
    items = result.scalars().all()
    processed = 0

    for item in items:
        item.status = SyncStatus.processing
        await db.flush()

        try:
            await _push_to_external_service(item)
            item.status = SyncStatus.completed
            item.processed_at = datetime.now(timezone.utc)
            processed += 1
            logger.info("Sync item %s completed", item.id)
        except Exception as exc:
            item.retry_count += 1
            if item.retry_count >= item.max_retries:
                item.status = SyncStatus.failed
                item.error_message = str(exc)
                logger.error(
                    "Sync item %s failed permanently after %d retries: %s",
                    item.id,
                    item.retry_count,
                    exc,
                )
            else:
                item.status = SyncStatus.pending
                item.error_message = str(exc)
                logger.warning(
                    "Sync item %s failed (attempt %d/%d): %s",
                    item.id,
                    item.retry_count,
                    item.max_retries,
                    exc,
                )
        await db.flush()

    return processed


async def get_pending_count(db: AsyncSession, household_id: uuid.UUID) -> int:
    """Return the number of pending sync queue items for a household."""
    result = await db.execute(
        select(func.count())
        .select_from(SyncQueueItem)
        .where(
            SyncQueueItem.household_id == household_id,
            SyncQueueItem.status == SyncStatus.pending,
        )
    )
    return result.scalar_one()


async def retry_failed(db: AsyncSession, household_id: uuid.UUID) -> int:
    """Reset failed items that haven't exceeded max_retries back to pending.

    Returns the number of items reset.
    """
    result = await db.execute(
        update(SyncQueueItem)
        .where(
            SyncQueueItem.household_id == household_id,
            SyncQueueItem.status == SyncStatus.failed,
            SyncQueueItem.retry_count < SyncQueueItem.max_retries,
        )
        .values(status=SyncStatus.pending, error_message=None)
    )
    count = result.rowcount  # type: ignore[assignment]
    if count:
        logger.info("Reset %d failed sync items to pending for household %s", count, household_id)
    return count


async def _push_to_external_service(item: SyncQueueItem) -> None:
    """Push a sync queue item to the appropriate external service.

    This is a dispatch stub — extend with real integration logic
    (e.g. Todoist, Google Calendar) based on ``item.entity_type``.
    """
    logger.debug(
        "Pushing %s %s (action=%s) to external service",
        item.entity_type,
        item.entity_id,
        item.action.value,
    )
    # TODO: dispatch to the correct integration client based on entity_type
