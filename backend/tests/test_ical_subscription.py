"""Tests for the lightweight iCal subscription flow."""
from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import patch

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calendar import CalendarProvider, SourceCalendar
from app.models.user import Household

pytestmark = pytest.mark.asyncio


# Sample iCal payload with two events.
_SAMPLE_ICS = (
    "BEGIN:VCALENDAR\r\n"
    "VERSION:2.0\r\n"
    "PRODID:-//Test//EN\r\n"
    "BEGIN:VEVENT\r\n"
    "UID:evt-1@example.com\r\n"
    "SUMMARY:Soccer practice\r\n"
    "DTSTART:20260501T220000Z\r\n"
    "DTEND:20260501T230000Z\r\n"
    "END:VEVENT\r\n"
    "BEGIN:VEVENT\r\n"
    "UID:evt-2@example.com\r\n"
    "SUMMARY:Dentist\r\n"
    "DTSTART:20260503T140000Z\r\n"
    "DTEND:20260503T150000Z\r\n"
    "END:VEVENT\r\n"
    "END:VCALENDAR\r\n"
)


def _patch_fetch(text: str) -> Any:
    """Patch ICalSubscription's HTTP GET to return canned text."""

    class _Resp:
        def __init__(self, t: str) -> None:
            self.text = t

        def raise_for_status(self) -> None:
            pass

    class _AsyncCM:
        def __init__(self, t: str) -> None:
            self._t = t

        async def __aenter__(self) -> "_AsyncCM":
            return self

        async def __aexit__(self, *_: Any) -> None:
            return None

        async def get(self, _url: str) -> _Resp:
            return _Resp(self._t)

    return patch(
        "app.integrations.caldav_client.httpx.AsyncClient",
        lambda **_: _AsyncCM(text),
    )


async def test_subscribe_ical_success(
    authed_client: AsyncClient,
    sample_household: Household,
    db_session: AsyncSession,
) -> None:
    with _patch_fetch(_SAMPLE_ICS), patch(
        "app.api.integrations.sync_single_calendar_task.delay"
    ) as mock_task:
        resp = await authed_client.post(
            "/api/integrations/ical/subscribe",
            json={
                "household_id": str(sample_household.id),
                "name": "Mom's Google Calendar",
                "ical_url": "https://calendar.google.com/calendar/ical/foo/private-bar/basic.ics",
            },
        )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["events_preview_count"] == 2
    assert body["sync_queued"] is True
    mock_task.assert_called_once()

    result = await db_session.execute(
        select(SourceCalendar).where(SourceCalendar.id == uuid.UUID(body["id"]))
    )
    cal = result.scalars().one()
    assert cal.provider == CalendarProvider.ical
    assert cal.is_read_only is True
    assert cal.external_id and cal.external_id.endswith("/basic.ics")


async def test_subscribe_ical_invalid_url_rejected(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    resp = await authed_client.post(
        "/api/integrations/ical/subscribe",
        json={
            "household_id": str(sample_household.id),
            "name": "Bad",
            "ical_url": "not a url",
        },
    )
    assert resp.status_code == 422


async def test_subscribe_ical_unfetchable_url_rejected(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    def _raise(*_a: Any, **_k: Any) -> Any:
        raise httpx.ConnectError("DNS failure")

    with patch(
        "app.integrations.caldav_client.httpx.AsyncClient.get",
        new=_raise,
    ):
        resp = await authed_client.post(
            "/api/integrations/ical/subscribe",
            json={
                "household_id": str(sample_household.id),
                "name": "Unreachable",
                "ical_url": "https://example.invalid/cal.ics",
            },
        )
    assert resp.status_code == 422


async def test_subscribe_ical_empty_calendar_rejected(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    empty = "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nEND:VCALENDAR\r\n"
    with _patch_fetch(empty):
        resp = await authed_client.post(
            "/api/integrations/ical/subscribe",
            json={
                "household_id": str(sample_household.id),
                "name": "Empty",
                "ical_url": "https://example.com/empty.ics",
            },
        )
    assert resp.status_code == 422
    assert "No events found" in resp.json()["detail"]


async def test_subscribe_ical_cross_household_forbidden(
    second_authed_client: AsyncClient, sample_household: Household
) -> None:
    with _patch_fetch(_SAMPLE_ICS):
        resp = await second_authed_client.post(
            "/api/integrations/ical/subscribe",
            json={
                "household_id": str(sample_household.id),
                "name": "Sneak",
                "ical_url": "https://example.com/cal.ics",
            },
        )
    assert resp.status_code == 403


async def test_unsubscribe_ical(
    authed_client: AsyncClient,
    sample_household: Household,
    db_session: AsyncSession,
) -> None:
    cal = SourceCalendar(
        household_id=sample_household.id,
        name="Old sub",
        provider=CalendarProvider.ical,
        external_id="https://example.com/old.ics",
        is_read_only=True,
    )
    db_session.add(cal)
    await db_session.flush()
    cal_id = cal.id

    resp = await authed_client.delete(f"/api/integrations/ical/{cal_id}")
    assert resp.status_code == 204

    result = await db_session.execute(
        select(SourceCalendar).where(SourceCalendar.id == cal_id)
    )
    assert result.scalars().first() is None


async def test_unsubscribe_ical_rejects_non_ical(
    authed_client: AsyncClient,
    sample_household: Household,
    db_session: AsyncSession,
) -> None:
    cal = SourceCalendar(
        household_id=sample_household.id,
        name="Local",
        provider=CalendarProvider.local,
    )
    db_session.add(cal)
    await db_session.flush()

    resp = await authed_client.delete(f"/api/integrations/ical/{cal.id}")
    assert resp.status_code == 400
