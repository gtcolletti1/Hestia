"""Celery tasks for calendar synchronisation."""


import asyncio
import logging
import uuid

from app.database import async_session
from app.models.calendar import SourceCalendar
from app.services.calendar_sync import (
    sync_all_calendars as _sync_all,
    sync_calendar as _sync_one,
)
from app.tasks import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from a synchronous Celery worker."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_single_calendar_task(self, source_calendar_id: str) -> dict:
    """On-demand sync for a single source calendar."""
    logger.info("Task: syncing calendar %s", source_calendar_id)

    async def _run():
        async with async_session() as db:
            try:
                cal = await db.get(
                    SourceCalendar, uuid.UUID(source_calendar_id)
                )
                if not cal:
                    logger.error("Calendar %s not found", source_calendar_id)
                    return {"error": "not found"}

                result = await _sync_one(db, cal)
                await db.commit()
                return result
            except Exception:
                await db.rollback()
                raise

    try:
        return _run_async(_run())
    except Exception as exc:
        logger.exception("sync_single_calendar_task failed for %s", source_calendar_id)
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=120)
def sync_all_calendars_task(self, household_id: str) -> list[dict]:
    """Periodic task that syncs all external calendars for a household."""
    logger.info("Task: syncing all calendars for household %s", household_id)

    async def _run():
        async with async_session() as db:
            try:
                results = await _sync_all(db, uuid.UUID(household_id))
                await db.commit()
                return results
            except Exception:
                await db.rollback()
                raise

    try:
        return _run_async(_run())
    except Exception as exc:
        logger.exception("sync_all_calendars_task failed for %s", household_id)
        raise self.retry(exc=exc)


# ── Celery Beat schedule ─────────────────────────────────────────────────────

from app.config import get_settings  # noqa: E402

_settings = get_settings()

celery_app.conf.beat_schedule = {
    **getattr(celery_app.conf, "beat_schedule", {}),
    "sync-all-calendars-periodic": {
        "task": "app.tasks.calendar_sync.sync_all_calendars_task",
        "schedule": _settings.CALENDAR_SYNC_INTERVAL,
        "options": {"expires": _settings.CALENDAR_SYNC_INTERVAL},
    },
}
