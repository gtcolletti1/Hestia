"""Household-level export / import (JSON backup & restore).

Scope: every household-scoped table EXCEPT integration credentials
(`oauth_credentials`) and `sync_queue_items`, which are environment-specific
and would leak secrets.

The JSON shape is a flat per-table dump of raw column values, so it stays
resilient to additive schema changes — new nullable columns just appear
in newer exports without breaking older readers.

Restore is REPLACE semantics: every household-scoped row in the included
tables is deleted before the backup is reinserted (in dependency order).
The household row itself is not deleted — its settings + name are
overwritten in place so the auth context survives.
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, time, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calendar import Event, SourceCalendar
from app.models.list import ListItem, TaskList
from app.models.meal import MealPlan
from app.models.note import Note
from app.models.photo import Photo
from app.models.reminder import Reminder
from app.models.reward import PointLedger, Reward
from app.models.routine import (
    Routine,
    RoutineCompletion,
    RoutineOverride,
    RoutineStep,
)
from app.models.school_closure import SchoolClosure
from app.models.user import Household, Profile

# Order matters for both export (informational) and restore (parents → children).
# Each entry is (key, model, parent_chain). `parent_chain` is the SQL-only
# delete predicate used during wipe — for tables that don't have
# `household_id` directly, we filter via a JOIN-equivalent subquery.
EXPORT_VERSION = 1


def _serialize_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (datetime,)):
        return value.isoformat()
    if isinstance(value, (date, time)):
        return value.isoformat()
    if isinstance(value, enum.Enum):
        return value.value
    return value


def _row_to_dict(row: Any) -> dict[str, Any]:
    return {col.name: _serialize_value(getattr(row, col.name)) for col in row.__table__.columns}


def _coerce(model: Any, payload: dict[str, Any]) -> dict[str, Any]:
    """Map raw JSON values back into Python types the SQLAlchemy column expects."""
    from sqlalchemy import Date, DateTime, Time
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID
    from sqlalchemy.types import Enum as SAEnum

    out: dict[str, Any] = {}
    cols = {c.name: c for c in model.__table__.columns}
    for key, raw in payload.items():
        col = cols.get(key)
        if col is None:
            # Forward-compat: ignore unknown keys from older or newer backups.
            continue
        if raw is None:
            out[key] = None
            continue
        col_type = col.type
        try:
            if isinstance(col_type, PG_UUID) or (hasattr(col_type, "python_type") and col_type.python_type is uuid.UUID):
                out[key] = uuid.UUID(raw) if not isinstance(raw, uuid.UUID) else raw
            elif isinstance(col_type, DateTime):
                out[key] = datetime.fromisoformat(raw) if isinstance(raw, str) else raw
            elif isinstance(col_type, Date):
                out[key] = date.fromisoformat(raw) if isinstance(raw, str) else raw
            elif isinstance(col_type, Time):
                out[key] = time.fromisoformat(raw) if isinstance(raw, str) else raw
            elif isinstance(col_type, SAEnum):
                # Pydantic-style enum coercion via the column's enum class
                enum_cls = col_type.enum_class
                if enum_cls is not None and not isinstance(raw, enum_cls):
                    out[key] = enum_cls(raw)
                else:
                    out[key] = raw
            else:
                out[key] = raw
        except Exception:
            # Surface a clean validation error rather than a 500 deep in SQLAlchemy.
            raise ValueError(f"Could not coerce field {model.__tablename__}.{key} value {raw!r}")
    return out


# ── Export ───────────────────────────────────────────────────────────────────

# (key, model). Order = restore order (parents before children).
EXPORTED_TABLES_HOUSEHOLD_DIRECT = [
    ("profiles", Profile),
    ("source_calendars", SourceCalendar),
    ("routines", Routine),
    ("task_lists", TaskList),
    ("meal_plans", MealPlan),
    ("notes", Note),
    ("photos", Photo),
    ("rewards", Reward),
    ("school_closures", SchoolClosure),
]

# (key, model, parent_model, fk_to_parent). Filtered via parent.household_id.
EXPORTED_TABLES_INDIRECT = [
    ("events", Event, SourceCalendar, "source_calendar_id"),
    ("reminders", Reminder, Event, "event_id"),
    ("routine_steps", RoutineStep, Routine, "routine_id"),
    ("routine_completions", RoutineCompletion, Routine, "routine_id"),
    ("routine_overrides", RoutineOverride, Routine, "routine_id"),
    ("list_items", ListItem, TaskList, "list_id"),
    # PointLedger: filter via Profile (each ledger row has profile_id)
    ("point_ledger", PointLedger, Profile, "profile_id"),
]


async def export_household(db: AsyncSession, household_id: uuid.UUID) -> dict[str, Any]:
    """Build a JSON-serializable snapshot of every household-scoped row."""
    household = (await db.execute(select(Household).where(Household.id == household_id))).scalar_one()

    payload: dict[str, Any] = {
        "version": EXPORT_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "household": {
            "id": str(household.id),
            "name": household.name,
            "settings": household.settings or {},
        },
    }

    # Resolve allowed-IDs per table so children can filter via "FK IN (...)"
    # without needing household_id directly. Built up as we walk parents first.
    allowed_ids: dict[str, set[uuid.UUID]] = {}

    for key, model in EXPORTED_TABLES_HOUSEHOLD_DIRECT:
        rows = (await db.execute(select(model).where(model.household_id == household_id))).scalars().all()
        payload[key] = [_row_to_dict(r) for r in rows]
        allowed_ids[model.__tablename__] = {r.id for r in rows}

    for key, model, parent, fk in EXPORTED_TABLES_INDIRECT:
        parent_ids = allowed_ids.get(parent.__tablename__, set())
        if not parent_ids:
            payload[key] = []
            allowed_ids[model.__tablename__] = set()
            continue
        rows = (
            await db.execute(select(model).where(getattr(model, fk).in_(parent_ids)))
        ).scalars().all()
        payload[key] = [_row_to_dict(r) for r in rows]
        allowed_ids[model.__tablename__] = {r.id for r in rows}

    return payload


# ── Import (REPLACE semantics) ───────────────────────────────────────────────


async def import_household(db: AsyncSession, household_id: uuid.UUID, backup: dict[str, Any]) -> dict[str, int]:
    """Wipe + restore household-scoped tables from a backup payload.

    Returns a per-table count of inserted rows for reporting back to the UI.
    """
    if not isinstance(backup, dict) or "version" not in backup:
        raise ValueError("Backup payload missing 'version' field")
    if backup.get("version") != EXPORT_VERSION:
        raise ValueError(
            f"Unsupported backup version {backup.get('version')!r} (expected {EXPORT_VERSION})"
        )

    household = (await db.execute(select(Household).where(Household.id == household_id))).scalar_one()

    # Wipe in REVERSE dependency order (children first).
    # Build allowed-IDs per parent table once so children can filter via FK IN (...).
    allowed_parent_ids: dict[str, set[uuid.UUID]] = {}
    for _key, model in EXPORTED_TABLES_HOUSEHOLD_DIRECT:
        ids = (
            await db.execute(select(model.id).where(model.household_id == household_id))
        ).scalars().all()
        allowed_parent_ids[model.__tablename__] = set(ids)
    # Resolve indirect parents (e.g. Event under SourceCalendar) so deeper
    # children (Reminder) can filter on those IDs too.
    for _key, model, parent, fk in EXPORTED_TABLES_INDIRECT:
        parent_ids = allowed_parent_ids.get(parent.__tablename__, set())
        if parent_ids:
            ids = (
                await db.execute(select(model.id).where(getattr(model, fk).in_(parent_ids)))
            ).scalars().all()
        else:
            ids = []
        allowed_parent_ids[model.__tablename__] = set(ids)

    for _key, model, parent, fk in reversed(EXPORTED_TABLES_INDIRECT):
        parent_ids = allowed_parent_ids.get(parent.__tablename__, set())
        if not parent_ids:
            continue
        await db.execute(delete(model).where(getattr(model, fk).in_(parent_ids)))

    for _key, model in reversed(EXPORTED_TABLES_HOUSEHOLD_DIRECT):
        await db.execute(delete(model).where(model.household_id == household_id))

    await db.flush()

    # Restore household settings + name
    h_payload = backup.get("household") or {}
    if "name" in h_payload:
        household.name = h_payload["name"]
    if "settings" in h_payload:
        household.settings = h_payload["settings"] or {}

    counts: dict[str, int] = {}

    # Insert direct tables (parents) first, flushing after each so FK references
    # to just-inserted rows work for tables added later in the same loop.
    for key, model in EXPORTED_TABLES_HOUSEHOLD_DIRECT:
        rows = backup.get(key) or []
        for raw in rows:
            data = _coerce(model, raw)
            # Force the household_id to the current household even if the
            # backup was taken from a different one — prevents cross-household
            # contamination via crafted payloads.
            data["household_id"] = household_id
            db.add(model(**data))
        await db.flush()
        counts[key] = len(rows)

    # Insert indirect tables (children).
    for key, model, _parent, _fk in EXPORTED_TABLES_INDIRECT:
        rows = backup.get(key) or []
        for raw in rows:
            data = _coerce(model, raw)
            db.add(model(**data))
        await db.flush()
        counts[key] = len(rows)

    return counts
