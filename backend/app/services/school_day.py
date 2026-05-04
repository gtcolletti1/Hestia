"""School-day calendar helper.

Determines whether a given date is a "school day" for a household so
routine steps flagged ``school_day_only`` can be auto-hidden on weekends,
US federal holidays, and admin-marked closures (snow days, in-service
days, district holidays).

Holiday source comes from the `holidays` package, defaulting to US
federal holidays. The household's ``settings`` JSON may override the
country / subdivision via ``holiday_country`` and ``holiday_subdiv``.

Manual closures live in the ``school_closures`` table (admin-managed
from the AdminPage Settings panel).
"""
from __future__ import annotations

import logging
import uuid
from datetime import date
from functools import lru_cache

import holidays
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.school_closure import SchoolClosure
from app.models.user import Household

logger = logging.getLogger(__name__)


@lru_cache(maxsize=64)
def _holiday_set(country: str, subdiv: str | None, year: int) -> frozenset[date]:
    """Cached set of holiday dates for a country/subdivision/year.

    The `holidays` package returns a dict-like object; we materialise a
    frozenset of date keys for cheap membership checks.
    """
    return frozenset(_holiday_map(country, subdiv, year).keys())


@lru_cache(maxsize=64)
def _holiday_map(country: str, subdiv: str | None, year: int) -> dict[date, str]:
    """Cached date → human-readable holiday name map."""
    try:
        cal = holidays.country_holidays(
            country, subdiv=subdiv, years=[year]
        )
    except (KeyError, NotImplementedError) as exc:
        logger.warning(
            "Unknown holiday country/subdiv %r/%r (%s); falling back to US",
            country,
            subdiv,
            exc,
        )
        cal = holidays.country_holidays("US", years=[year])
    return {d: str(name) for d, name in cal.items()}


def is_us_federal_holiday(target: date) -> bool:
    """Convenience wrapper for tests / callers without a household."""
    return target in _holiday_set("US", None, target.year)


async def load_school_day_context(
    db: AsyncSession, household_id: uuid.UUID, year: int
) -> "SchoolDayContext":
    """Load everything needed to answer ``is_school_day`` for one year.

    Returns a small immutable context callers can reuse across many date
    checks without re-hitting the DB or re-instantiating the holidays
    calendar.
    """
    household = (
        await db.execute(
            select(Household).where(Household.id == household_id)
        )
    ).scalar_one_or_none()

    settings = (household.settings if household else None) or {}
    country = str(settings.get("holiday_country") or "US").upper()
    subdiv_raw = settings.get("holiday_subdiv")
    subdiv = str(subdiv_raw).upper() if subdiv_raw else None

    rows = (
        await db.execute(
            select(SchoolClosure.date, SchoolClosure.reason).where(
                SchoolClosure.household_id == household_id
            )
        )
    ).all()
    closures: dict[date, str | None] = {row[0]: row[1] for row in rows}

    return SchoolDayContext(
        country=country,
        subdiv=subdiv,
        year=year,
        manual_closures=closures,
    )


class SchoolDayContext:
    """Immutable bundle of everything ``is_school_day`` needs."""

    __slots__ = ("country", "subdiv", "year", "manual_closures")

    def __init__(
        self,
        country: str,
        subdiv: str | None,
        year: int,
        manual_closures: "dict[date, str | None] | frozenset[date]",
    ) -> None:
        self.country = country
        self.subdiv = subdiv
        self.year = year
        # Accept either the new dict form or the legacy frozenset form
        # (older tests construct contexts directly with frozenset()).
        if isinstance(manual_closures, frozenset):
            self.manual_closures: dict[date, str | None] = {
                d: None for d in manual_closures
            }
        else:
            self.manual_closures = dict(manual_closures)

    def is_school_day(self, target: date) -> bool:
        """True iff ``target`` is a weekday, not a holiday, not a closure."""
        if target.weekday() >= 5:
            return False
        if target in self.manual_closures:
            return False
        holiday_dates = _holiday_set(self.country, self.subdiv, target.year)
        if target in holiday_dates:
            return False
        return True

    def reason_for(self, target: date) -> str | None:
        """Human-readable reason ``target`` is *not* a school day, or None.

        Returned reasons (in priority order):
          - Admin closure reason (e.g. "Snow day"); falls back to
            ``"School closure"`` when no reason was recorded.
          - Holiday name from the ``holidays`` package
            (e.g. ``"Martin Luther King Jr. Day"``).
          - ``None`` for weekends and for school days — the splash/home
            banner is meant to call out non-obvious closures, so we
            deliberately skip Saturdays/Sundays.
        """
        if target in self.manual_closures:
            return self.manual_closures[target] or "School closure"
        holiday_map = _holiday_map(self.country, self.subdiv, target.year)
        if target in holiday_map:
            return holiday_map[target]
        return None


async def count_hidden_school_day_steps(
    db: AsyncSession,
    household_id: uuid.UUID,
    today: date,
) -> int:
    """Count active routine steps that are flagged ``school_day_only`` and
    scheduled for ``today`` (per the routine's day-of-week mask + the
    step's optional override). Used by splash/dashboard to populate the
    school-day banner with a quick "N steps hidden" hint.

    This is a coarse signal — it does not account for vacation overrides
    or per-routine pauses; the banner simply tells the user "today is a
    closure and these flagged steps are skipped".
    """
    # Lazy imports to avoid circular dependency at module load.
    from sqlalchemy.orm import selectinload
    from app.models.routine import Routine

    weekday = today.weekday()
    rows = (
        await db.execute(
            select(Routine)
            .options(selectinload(Routine.steps))
            .where(
                Routine.household_id == household_id,
                Routine.is_active.is_(True),
            )
        )
    ).scalars().all()

    hidden = 0
    for r in rows:
        routine_days = set(r.days_of_week or [0, 1, 2, 3, 4, 5, 6])
        if weekday not in routine_days:
            continue
        for s in r.steps:
            if not getattr(s, "school_day_only", False):
                continue
            step_days = s.days_of_week
            if step_days is not None and weekday not in set(step_days):
                continue
            hidden += 1
    return hidden
