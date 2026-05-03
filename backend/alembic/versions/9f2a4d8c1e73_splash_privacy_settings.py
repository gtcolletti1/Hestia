"""Splash & pre-login privacy settings (PRD v2.2 §2.12).

Migrates each household's settings JSON:

* Map the deprecated ``privacy_mode`` boolean to the new
  ``splash_calendar_mode`` enum:
    - ``True``  → ``"busy_only"``  (passersby see Busy + time + color dot)
    - ``False`` → ``"off"``        (full details, original behavior)
  …then drop the ``privacy_mode`` key.
* Seed the new ``splash_*`` keys with their defaults if not already set.

Schema is unchanged (settings is a JSON column on ``households``); this
is purely a data migration so it runs the same way on PostgreSQL and
SQLite.

Revision ID: 9f2a4d8c1e73
Revises: 8d1e7a2c4b59
Create Date: 2026-05-03 15:40:00.000000
"""
from __future__ import annotations

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "9f2a4d8c1e73"
down_revision: Union[str, None] = "8d1e7a2c4b59"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Defaults must mirror app/schemas/admin.py::HouseholdSettings.
_NEW_DEFAULTS: dict[str, object] = {
    "splash_mode": "ambient",
    "splash_alternating_ambient_seconds": 60,
    "splash_alternating_photo_seconds": 60,
    "splash_agenda_max_days": 3,
    "splash_calendar_mode": "off",
    "splash_show_routines": True,
    "splash_show_meals": False,
    "splash_show_weather": True,
    "splash_show_messages": False,
}


def _coerce_settings(value: object) -> dict | None:
    """SQLite stores JSON as TEXT; PostgreSQL hands us a dict already."""
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, (str, bytes)):
        try:
            parsed = json.loads(value)
        except (ValueError, TypeError):
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, settings FROM households")).fetchall()

    for row in rows:
        household_id = row[0]
        current = _coerce_settings(row[1]) or {}

        # Map the legacy boolean before discarding it. Falling back to ``"off"``
        # when ``privacy_mode`` is missing or False mirrors the prior behavior.
        legacy = current.pop("privacy_mode", None)
        derived_calendar_mode = "busy_only" if legacy is True else "off"

        # Seed new keys only if not already present. The derived mode wins
        # for the splash_calendar_mode default so existing privacy_mode=True
        # users retain their disclosure preference; existing splash_* keys
        # (if any from a partial migration) are preserved as-is.
        defaults = {**_NEW_DEFAULTS, "splash_calendar_mode": derived_calendar_mode}
        for key, default in defaults.items():
            current.setdefault(key, default)

        bind.execute(
            sa.text("UPDATE households SET settings = :s WHERE id = :id"),
            {"s": json.dumps(current), "id": household_id},
        )


def downgrade() -> None:
    """Restore ``privacy_mode`` from ``splash_calendar_mode`` and drop new keys.

    The mapping is intentionally lossy: ``hidden`` collapses to ``True``
    along with ``busy_only`` because the old boolean only had two states.
    """
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, settings FROM households")).fetchall()

    for row in rows:
        household_id = row[0]
        current = _coerce_settings(row[1]) or {}

        mode = current.get("splash_calendar_mode", "off")
        current["privacy_mode"] = mode in {"busy_only", "hidden"}

        for key in _NEW_DEFAULTS:
            current.pop(key, None)

        bind.execute(
            sa.text("UPDATE households SET settings = :s WHERE id = :id"),
            {"s": json.dumps(current), "id": household_id},
        )
