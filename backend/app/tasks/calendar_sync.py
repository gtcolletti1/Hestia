"""Celery tasks for calendar synchronisation."""


import asyncio
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import get_settings
from app.models.calendar import SourceCalendar
from app.models.user import Household
from app.services.calendar_sync import (
    sync_all_calendars as _sync_all,
    sync_calendar as _sync_one,
)
from app.tasks import celery_app

logger = logging.getLogger(__name__)

_settings = get_settings()


def _run_async(coro_factory):
    """Run an async coroutine in a fresh event loop with a fresh DB engine.

    Celery's prefork worker reuses module-level state across tasks, but the
    SQLAlchemy async engine's pooled asyncpg connections are bound to the
    event loop they were created on. Reusing them from a new loop raises
    ``InterfaceError: another operation is in progress``. We therefore build a
    short-lived ``NullPool`` engine per task — every connection is opened and
    closed within this single loop.
    """
    loop = asyncio.new_event_loop()
    try:
        async def _wrapper():
            engine = create_async_engine(
                _settings.DATABASE_URL, poolclass=NullPool
            )
            session_maker = async_sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False
            )
            try:
                return await coro_factory(session_maker)
            finally:
                await engine.dispose()

        return loop.run_until_complete(_wrapper())
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_single_calendar_task(self, source_calendar_id: str) -> dict:
    """On-demand sync for a single source calendar."""
    logger.info("Task: syncing calendar %s", source_calendar_id)

    async def _run(session_maker):
        async with session_maker() as db:
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
        return _run_async(_run)
    except Exception as exc:
        logger.exception("sync_single_calendar_task failed for %s", source_calendar_id)
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=120)
def sync_all_calendars_task(self, household_id: str) -> list[dict]:
    """Sync all external calendars for a single household."""
    logger.info("Task: syncing all calendars for household %s", household_id)

    async def _run(session_maker):
        async with session_maker() as db:
            try:
                results = await _sync_all(db, uuid.UUID(household_id))
                await db.commit()
                return results
            except Exception:
                await db.rollback()
                raise

    try:
        return _run_async(_run)
    except Exception as exc:
        logger.exception("sync_all_calendars_task failed for %s", household_id)
        raise self.retry(exc=exc)


@celery_app.task(name="app.tasks.calendar_sync.sync_all_households_task")
def sync_all_households_task() -> dict:
    """Periodic fan-out: enqueue per-household syncs for every household."""

    async def _run(session_maker):
        async with session_maker() as db:
            result = await db.execute(select(Household.id))
            return [str(hid) for hid in result.scalars().all()]

    try:
        household_ids = _run_async(_run)
    except Exception:
        logger.exception("sync_all_households_task: failed to enumerate households")
        return {"dispatched": 0}

    for hid in household_ids:
        sync_all_calendars_task.delay(hid)
    logger.info("Dispatched periodic sync for %d household(s)", len(household_ids))
    return {"dispatched": len(household_ids)}


# ── Celery Beat schedule ─────────────────────────────────────────────────────

celery_app.conf.beat_schedule = {
    **getattr(celery_app.conf, "beat_schedule", {}),
    "sync-all-calendars-periodic": {
        "task": "app.tasks.calendar_sync.sync_all_households_task",
        "schedule": _settings.CALENDAR_SYNC_INTERVAL,
        "options": {"expires": _settings.CALENDAR_SYNC_INTERVAL},
    },
}
