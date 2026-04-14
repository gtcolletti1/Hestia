"""Cross-household tests for integration endpoints (sync, status)."""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calendar import CalendarProvider, SourceCalendar
from app.models.user import Household, Profile

pytestmark = pytest.mark.asyncio


# ── Cross-household integration tests ────────────────────────────────────────


async def test_cross_household_trigger_sync(
    authed_client: AsyncClient,
    second_authed_client: AsyncClient,
    sample_household: Household,
    db_session: AsyncSession,
) -> None:
    """User from household B cannot trigger sync for household A's calendar."""
    cal = SourceCalendar(
        household_id=sample_household.id,
        name="Family Cal",
        provider=CalendarProvider.local,
    )
    db_session.add(cal)
    await db_session.flush()
    await db_session.refresh(cal)

    resp = await second_authed_client.get(
        f"/api/integrations/calendars/sync/{cal.id}",
    )
    assert resp.status_code == 403


async def test_cross_household_trigger_sync_all(
    second_authed_client: AsyncClient,
    sample_household: Household,
) -> None:
    """User from household B cannot trigger sync-all for household A."""
    resp = await second_authed_client.get(
        "/api/integrations/calendars/sync-all",
        params={"household_id": str(sample_household.id)},
    )
    assert resp.status_code == 403


async def test_cross_household_integration_status(
    second_authed_client: AsyncClient,
    sample_household: Household,
) -> None:
    """User from household B cannot view household A's integration status."""
    resp = await second_authed_client.get(
        "/api/integrations/status",
        params={"household_id": str(sample_household.id)},
    )
    assert resp.status_code == 403
