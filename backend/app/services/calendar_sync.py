"""Calendar synchronisation service.

Handles pulling events from external providers into the local database
and pushing local changes back out.
"""


import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.caldav_client import CalDAVClient, ICalSubscription
from app.integrations.google_calendar import (
    GoogleCalendarClient,
    map_google_event_to_local,
    map_local_event_to_google,
)
from app.integrations.outlook_calendar import (
    OutlookCalendarClient,
    map_local_event_to_outlook,
    map_outlook_event_to_local,
)
from app.models.calendar import CalendarProvider, Event, SourceCalendar
from app.models.integration import (
    OAuthCredential,
    OAuthProvider,
    SyncAction,
    SyncQueueItem,
    SyncStatus,
)

logger = logging.getLogger(__name__)


# ── Main sync entry point ────────────────────────────────────────────────────


async def sync_calendar(
    db: AsyncSession, source_calendar: SourceCalendar
) -> dict:
    """Synchronise a single SourceCalendar from its external provider.

    Returns a summary dict with counts of created, updated, and deleted
    events.
    """
    provider = source_calendar.provider
    logger.info(
        "Starting sync for calendar %s (provider=%s)",
        source_calendar.id,
        provider.value,
    )

    try:
        if provider == CalendarProvider.google:
            result = await _sync_google(db, source_calendar)
        elif provider == CalendarProvider.outlook:
            result = await _sync_outlook(db, source_calendar)
        elif provider == CalendarProvider.caldav:
            result = await _sync_caldav(db, source_calendar)
        elif provider == CalendarProvider.ical:
            result = await _sync_ical(db, source_calendar)
        else:
            logger.info("Skipping local-only calendar %s", source_calendar.id)
            return {"created": 0, "updated": 0, "deleted": 0}

        source_calendar.last_synced_at = datetime.now(timezone.utc)
        db.add(source_calendar)
        await db.flush()

        logger.info("Sync complete for calendar %s: %s", source_calendar.id, result)
        return result
    except Exception:
        logger.exception("Sync failed for calendar %s", source_calendar.id)
        raise


# ── Provider-specific sync implementations ───────────────────────────────────


async def _sync_google(
    db: AsyncSession, source_calendar: SourceCalendar
) -> dict:
    credential = await _get_credential(db, source_calendar, OAuthProvider.google)
    client = GoogleCalendarClient(credential)
    try:
        await client.refresh_token_if_needed(db)

        calendar_id = source_calendar.external_id or "primary"
        events, new_sync_token = await client.sync_events(
            calendar_id, source_calendar.sync_token
        )

        result = await _upsert_events(
            db,
            source_calendar,
            [map_google_event_to_local(e) for e in events if e.get("status") != "cancelled"],
            cancelled_ids=[
                e["id"] for e in events if e.get("status") == "cancelled"
            ],
        )

        source_calendar.sync_token = new_sync_token
        return result
    finally:
        await client.close()


async def _sync_outlook(
    db: AsyncSession, source_calendar: SourceCalendar
) -> dict:
    credential = await _get_credential(db, source_calendar, OAuthProvider.microsoft)
    client = OutlookCalendarClient(credential)
    try:
        await client.refresh_token_if_needed(db)

        calendar_id = source_calendar.external_id or ""
        events, new_delta_link = await client.sync_events(
            calendar_id, source_calendar.sync_token
        )

        # Outlook delta responses include @removed for deletions
        removed_ids = [
            e["id"]
            for e in events
            if "@removed" in e
        ]
        active_events = [e for e in events if "@removed" not in e]

        result = await _upsert_events(
            db,
            source_calendar,
            [map_outlook_event_to_local(e) for e in active_events],
            cancelled_ids=removed_ids,
        )

        source_calendar.sync_token = new_delta_link
        return result
    finally:
        await client.close()


async def _sync_caldav(
    db: AsyncSession, source_calendar: SourceCalendar
) -> dict:
    url = source_calendar.external_id or ""
    client = CalDAVClient(url)
    try:
        now = datetime.now(timezone.utc)
        from datetime import timedelta

        start = now - timedelta(days=30)
        end = now + timedelta(days=365)
        event_dicts = await client.fetch_events(start, end)

        result = await _upsert_events(db, source_calendar, event_dicts)
        return result
    finally:
        await client.close()


async def _sync_ical(
    db: AsyncSession, source_calendar: SourceCalendar
) -> dict:
    ical_url = source_calendar.external_id or ""
    sub = ICalSubscription()
    event_dicts = await sub.fetch_and_parse(ical_url)
    result = await _upsert_events(db, source_calendar, event_dicts)
    # Snapshot semantics for recurrence overrides: any local override row
    # whose (master_uid, recurrence_id) is no longer present in the feed must
    # be deleted, otherwise expansion will keep skipping a master occurrence
    # that should have come back.
    seen_overrides: set[tuple[str, datetime]] = {
        (e["master_external_id"], e["recurrence_id"])
        for e in event_dicts
        if e.get("recurrence_id") is not None and e.get("master_external_id")
    }
    pruned = await _prune_stale_overrides(db, source_calendar, seen_overrides)
    if pruned:
        result["deleted"] = result.get("deleted", 0) + pruned
    return result


# ── Shared helpers ───────────────────────────────────────────────────────────


async def _get_credential(
    db: AsyncSession,
    source_calendar: SourceCalendar,
    provider: OAuthProvider,
) -> OAuthCredential:
    """Look up the OAuth credential for the calendar's household."""
    stmt = select(OAuthCredential).where(
        OAuthCredential.household_id == source_calendar.household_id,
        OAuthCredential.provider == provider,
    )
    result = await db.execute(stmt)
    credential = result.scalars().first()
    if not credential:
        raise RuntimeError(
            f"No {provider.value} credential found for household "
            f"{source_calendar.household_id}"
        )
    return credential


async def _upsert_events(
    db: AsyncSession,
    source_calendar: SourceCalendar,
    event_dicts: list[dict],
    cancelled_ids: list[str] | None = None,
) -> dict:
    """Upsert a list of event dicts into the local database.

    Matches on (source_calendar_id, external_id). Returns counts.
    """
    created = 0
    updated = 0
    deleted = 0

    for edict in event_dicts:
        external_id = edict.get("external_id")
        if not external_id:
            continue

        stmt = select(Event).where(
            Event.source_calendar_id == source_calendar.id,
            Event.external_id == external_id,
        )
        result = await db.execute(stmt)
        existing = result.scalars().first()

        if existing:
            for key, value in edict.items():
                if key != "external_id":
                    setattr(existing, key, value)
            updated += 1
        else:
            event = Event(
                source_calendar_id=source_calendar.id,
                **edict,
            )
            db.add(event)
            created += 1

    # Handle deletions
    if cancelled_ids:
        stmt = select(Event).where(
            Event.source_calendar_id == source_calendar.id,
            Event.external_id.in_(cancelled_ids),
        )
        result = await db.execute(stmt)
        for event in result.scalars().all():
            await db.delete(event)
            deleted += 1

    await db.flush()
    return {"created": created, "updated": updated, "deleted": deleted}


async def _prune_stale_overrides(
    db: AsyncSession,
    source_calendar: SourceCalendar,
    seen: set[tuple[str, datetime]],
) -> int:
    """Delete override rows for this source calendar whose
    (master_external_id, recurrence_id) is not in the latest feed.

    This restores master occurrences whose modified-instance has been
    reverted or deleted upstream; without it the expansion logic would
    keep skipping that occurrence forever.
    """
    stmt = select(Event).where(
        Event.source_calendar_id == source_calendar.id,
        Event.recurrence_id.isnot(None),
    )
    result = await db.execute(stmt)
    deleted = 0
    for ev in result.scalars().all():
        key = (ev.master_external_id or "", ev.recurrence_id)
        if key not in seen:
            await db.delete(ev)
            deleted += 1
    if deleted:
        await db.flush()
    return deleted


# ── Bulk and push operations ─────────────────────────────────────────────────


async def sync_all_calendars(
    db: AsyncSession, household_id: uuid.UUID
) -> list[dict]:
    """Sync all source calendars for a household.

    Returns a list of per-calendar result dicts. Individual failures are
    caught and logged so one broken calendar doesn't block the others.
    """
    stmt = select(SourceCalendar).where(
        SourceCalendar.household_id == household_id,
        SourceCalendar.provider != CalendarProvider.local,
    )
    result = await db.execute(stmt)
    calendars = list(result.scalars().all())

    results: list[dict] = []
    for cal in calendars:
        try:
            sync_result = await sync_calendar(db, cal)
            results.append({"calendar_id": str(cal.id), **sync_result})
        except Exception:
            logger.exception("Failed to sync calendar %s, continuing", cal.id)
            results.append(
                {"calendar_id": str(cal.id), "error": "sync failed"}
            )

    return results


async def push_local_changes(
    db: AsyncSession, source_calendar: SourceCalendar
) -> int:
    """Push pending SyncQueue items to the external service.

    Returns the number of items successfully processed.
    """
    stmt = (
        select(SyncQueueItem)
        .where(
            SyncQueueItem.entity_type == "event",
            SyncQueueItem.status == SyncStatus.pending,
            SyncQueueItem.household_id == source_calendar.household_id,
        )
        .order_by(SyncQueueItem.created_at)
    )
    result = await db.execute(stmt)
    items = list(result.scalars().all())

    if not items:
        return 0

    provider = source_calendar.provider
    calendar_id = source_calendar.external_id or "primary"

    # Build provider client
    client: GoogleCalendarClient | OutlookCalendarClient | None = None
    try:
        if provider == CalendarProvider.google:
            cred = await _get_credential(db, source_calendar, OAuthProvider.google)
            client = GoogleCalendarClient(cred)
            await client.refresh_token_if_needed(db)
        elif provider == CalendarProvider.outlook:
            cred = await _get_credential(db, source_calendar, OAuthProvider.microsoft)
            client = OutlookCalendarClient(cred)
            await client.refresh_token_if_needed(db)
        else:
            logger.info(
                "Push not supported for provider %s", provider.value
            )
            return 0

        processed = 0
        for item in items:
            try:
                await _process_sync_item(db, client, calendar_id, source_calendar, item)
                item.status = SyncStatus.completed
                item.processed_at = datetime.now(timezone.utc)
                processed += 1
            except Exception as exc:
                logger.exception("Failed to push sync item %s", item.id)
                item.retry_count += 1
                item.error_message = str(exc)
                if item.retry_count >= item.max_retries:
                    item.status = SyncStatus.failed
                else:
                    item.status = SyncStatus.pending

        await db.flush()
        return processed
    finally:
        if client:
            await client.close()


async def _process_sync_item(
    db: AsyncSession,
    client: GoogleCalendarClient | OutlookCalendarClient,
    calendar_id: str,
    source_calendar: SourceCalendar,
    item: SyncQueueItem,
) -> None:
    """Process a single SyncQueueItem by pushing it to the external API."""
    event = await db.get(Event, item.entity_id)

    if item.action == SyncAction.create and event:
        if isinstance(client, GoogleCalendarClient):
            event_data = map_local_event_to_google(event)
            result = await client.create_event(calendar_id, event_data)
            event.external_id = result.get("id")
        else:
            event_data = map_local_event_to_outlook(event)
            result = await client.create_event(calendar_id, event_data)
            event.external_id = result.get("id")

    elif item.action == SyncAction.update and event and event.external_id:
        if isinstance(client, GoogleCalendarClient):
            event_data = map_local_event_to_google(event)
            await client.update_event(calendar_id, event.external_id, event_data)
        else:
            event_data = map_local_event_to_outlook(event)
            await client.update_event(calendar_id, event.external_id, event_data)

    elif item.action == SyncAction.delete:
        ext_id = (item.payload or {}).get("external_id", "")
        if ext_id:
            if isinstance(client, GoogleCalendarClient):
                await client.delete_event(calendar_id, ext_id)
            else:
                await client.delete_event(calendar_id, ext_id)
