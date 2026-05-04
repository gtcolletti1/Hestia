"""Shared event expansion / dedup helper.

Both the Calendar API list endpoint and the Dashboard / Splash agendas
need the same view of "what events fall in this time range?" — including:

* expanding RRULE-based recurrences into their actual occurrences,
* skipping master occurrences that have a recurrence override (so the
  override row is the only one that appears at that slot),
* honoring EXDATE entries on the master row,
* DST-correct expansion using the master's stored TZID.

This module centralises that logic so the three callers can't drift.
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dateutil.rrule import rrulestr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calendar import Event, SourceCalendar
from app.models.user import Profile

logger = logging.getLogger(__name__)


@dataclass
class ExpandedEvent:
    """An event occurrence with effective start/end and joined profile data.

    ``event`` is the underlying ORM row (for title, color, location, etc.).
    ``start_time`` / ``end_time`` are the *occurrence's* UTC instants, which
    differ from ``event.start_time`` / ``event.end_time`` for expanded
    recurring occurrences past the first.
    """

    event: Event
    start_time: datetime
    end_time: datetime
    profile_name: str | None
    profile_color: str | None


async def expand_events_in_range(
    db: AsyncSession,
    household_id: uuid.UUID,
    range_start: datetime,
    range_end: datetime,
    profile_id: uuid.UUID | None = None,
    source_calendar_id: uuid.UUID | None = None,
) -> list[ExpandedEvent]:
    """Return every event occurrence that overlaps [range_start, range_end).

    Inputs must be timezone-aware UTC datetimes. Output is sorted by
    effective start_time and contains no duplicates between a recurring
    master and its overridden instance.
    """

    # ── Non-recurring rows that touch the window ────────────────────────
    base_stmt = (
        select(Event, Profile.name.label("profile_name"), Profile.color.label("profile_color"))
        .join(SourceCalendar, Event.source_calendar_id == SourceCalendar.id)
        .outerjoin(Profile, Event.profile_id == Profile.id)
        .where(
            SourceCalendar.household_id == household_id,
            Event.start_time < range_end,
            Event.end_time >= range_start,
        )
    )
    if profile_id is not None:
        base_stmt = base_stmt.where(Event.profile_id == profile_id)
    if source_calendar_id is not None:
        base_stmt = base_stmt.where(Event.source_calendar_id == source_calendar_id)

    base_rows = (await db.execute(base_stmt)).all()

    # ── Recurring masters whose first occurrence is before range_end ────
    recur_stmt = (
        select(Event, Profile.name.label("profile_name"), Profile.color.label("profile_color"))
        .join(SourceCalendar, Event.source_calendar_id == SourceCalendar.id)
        .outerjoin(Profile, Event.profile_id == Profile.id)
        .where(
            SourceCalendar.household_id == household_id,
            Event.recurrence_rule.isnot(None),
            Event.start_time < range_end,
        )
    )
    if profile_id is not None:
        recur_stmt = recur_stmt.where(Event.profile_id == profile_id)
    if source_calendar_id is not None:
        recur_stmt = recur_stmt.where(Event.source_calendar_id == source_calendar_id)

    recur_rows = (await db.execute(recur_stmt)).all()

    # ── Per-master override map (recurrence_id -> "skip this slot") ─────
    override_stmt = (
        select(Event)
        .join(SourceCalendar, Event.source_calendar_id == SourceCalendar.id)
        .where(
            SourceCalendar.household_id == household_id,
            Event.recurrence_id.isnot(None),
        )
    )
    if profile_id is not None:
        override_stmt = override_stmt.where(Event.profile_id == profile_id)
    if source_calendar_id is not None:
        override_stmt = override_stmt.where(Event.source_calendar_id == source_calendar_id)

    override_rows = (await db.execute(override_stmt)).scalars().all()
    overrides_by_master: dict[tuple[uuid.UUID, str], list[datetime]] = defaultdict(list)
    for ov in override_rows:
        if ov.master_external_id and ov.recurrence_id is not None:
            overrides_by_master[(ov.source_calendar_id, ov.master_external_id)].append(
                ov.recurrence_id
            )

    output: list[ExpandedEvent] = []
    seen_master_ids: set[uuid.UUID] = set()

    # ── Pass 1: non-recurring rows + override rows pass through ─────────
    for event, p_name, p_color in base_rows:
        if event.recurrence_rule:
            # masters are handled by expansion below; never emit them raw
            continue
        seen_master_ids.add(event.id)
        start = _ensure_utc(event.start_time)
        end = _ensure_utc(event.end_time)
        output.append(
            ExpandedEvent(
                event=event,
                start_time=start,
                end_time=end,
                profile_name=p_name,
                profile_color=p_color,
            )
        )

    # ── Pass 2: expand each recurring master ────────────────────────────
    for ev, p_name, p_color in recur_rows:
        if ev.id in seen_master_ids:
            continue
        seen_master_ids.add(ev.id)

        duration = ev.end_time - ev.start_time

        try:
            master_tz = ZoneInfo(ev.start_tzid) if ev.start_tzid else timezone.utc
        except ZoneInfoNotFoundError:
            logger.warning(
                "Unknown TZID %r on event %s, falling back to UTC", ev.start_tzid, ev.id
            )
            master_tz = timezone.utc

        local_dtstart = _ensure_utc(ev.start_time).astimezone(master_tz).replace(tzinfo=None)
        local_range_start = range_start.astimezone(master_tz).replace(tzinfo=None)
        local_range_end = range_end.astimezone(master_tz).replace(tzinfo=None)

        skip_utc: set[datetime] = set()
        if ev.exdates:
            for raw in ev.exdates.split(","):
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    skip_utc.add(datetime.fromisoformat(raw))
                except ValueError:
                    logger.warning("Skipping malformed exdate %r on event %s", raw, ev.id)

        master_uid = ev.master_external_id or ev.external_id
        if master_uid:
            for rid in overrides_by_master.get((ev.source_calendar_id, master_uid), ()):
                skip_utc.add(rid if rid.tzinfo else rid.replace(tzinfo=timezone.utc))

        try:
            rule = rrulestr(ev.recurrence_rule, dtstart=local_dtstart)
            local_occs = rule.between(local_range_start, local_range_end, inc=True)
        except (ValueError, TypeError):
            ev_start = _ensure_utc(ev.start_time)
            ev_end = _ensure_utc(ev.end_time)
            if ev_start < range_end and ev_end >= range_start:
                output.append(
                    ExpandedEvent(
                        event=ev,
                        start_time=ev_start,
                        end_time=ev_end,
                        profile_name=p_name,
                        profile_color=p_color,
                    )
                )
            continue

        for local_occ in local_occs:
            occ_start = local_occ.replace(tzinfo=master_tz).astimezone(timezone.utc)
            if occ_start in skip_utc:
                continue
            occ_end = occ_start + duration
            output.append(
                ExpandedEvent(
                    event=ev,
                    start_time=occ_start,
                    end_time=occ_end,
                    profile_name=p_name,
                    profile_color=p_color,
                )
            )

    output.sort(key=lambda e: e.start_time)
    return output


def _ensure_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
