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
    return frozenset(cal.keys())


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

    closures = (
        await db.execute(
            select(SchoolClosure.date).where(
                SchoolClosure.household_id == household_id
            )
        )
    ).scalars().all()

    return SchoolDayContext(
        country=country,
        subdiv=subdiv,
        year=year,
        manual_closures=frozenset(closures),
    )


class SchoolDayContext:
    """Immutable bundle of everything ``is_school_day`` needs."""

    __slots__ = ("country", "subdiv", "year", "manual_closures")

    def __init__(
        self,
        country: str,
        subdiv: str | None,
        year: int,
        manual_closures: frozenset[date],
    ) -> None:
        self.country = country
        self.subdiv = subdiv
        self.year = year
        self.manual_closures = manual_closures

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
