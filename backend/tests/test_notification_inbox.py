"""Tests for the notification inbox / dashboard bell."""
from __future__ import annotations

import datetime as dt
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calendar import Event, SourceCalendar
from app.models.notification import NotificationEntry
from app.models.reminder import Reminder
from app.models.user import Household, Profile, ProfileRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture()
async def household_other_member(
    db_session: AsyncSession, sample_household: Household
) -> Profile:
    p = Profile(
        household_id=sample_household.id,
        name="Sibling",
        color="#33A1FF",
        role=ProfileRole.kid,
        pin_hash=pwd_context.hash("4321"),
        is_active=True,
    )
    db_session.add(p)
    await db_session.flush()
    await db_session.refresh(p)
    return p


async def _add_entry(
    db: AsyncSession,
    household_id: uuid.UUID,
    *,
    profile_id: uuid.UUID | None = None,
    title: str = "Test",
    read: bool = False,
) -> NotificationEntry:
    e = NotificationEntry(
        household_id=household_id,
        profile_id=profile_id,
        kind="info",
        title=title,
        body="body",
        read_at=dt.datetime.utcnow() if read else None,
    )
    db.add(e)
    await db.flush()
    await db.refresh(e)
    return e


# ── Inbox listing & visibility ──────────────────────────────────────────────


async def test_inbox_lists_household_and_self_entries(
    authed_client: AsyncClient,
    db_session: AsyncSession,
    sample_household: Household,
    sample_profile: Profile,
    household_other_member: Profile,
) -> None:
    await _add_entry(db_session, sample_household.id, title="household one")
    await _add_entry(
        db_session, sample_household.id, profile_id=sample_profile.id, title="self one"
    )
    await _add_entry(
        db_session,
        sample_household.id,
        profile_id=household_other_member.id,
        title="not for me",
    )

    resp = await authed_client.get(
        "/api/notifications/inbox", params={"household_id": str(sample_household.id)}
    )
    assert resp.status_code == 200
    titles = [e["title"] for e in resp.json()]
    assert "household one" in titles
    assert "self one" in titles
    assert "not for me" not in titles


async def test_inbox_unread_only_filter(
    authed_client: AsyncClient,
    db_session: AsyncSession,
    sample_household: Household,
) -> None:
    await _add_entry(db_session, sample_household.id, title="unread")
    await _add_entry(db_session, sample_household.id, title="already read", read=True)
    resp = await authed_client.get(
        "/api/notifications/inbox",
        params={"household_id": str(sample_household.id), "unread_only": "true"},
    )
    titles = [e["title"] for e in resp.json()]
    assert "unread" in titles
    assert "already read" not in titles


async def test_inbox_unread_count(
    authed_client: AsyncClient,
    db_session: AsyncSession,
    sample_household: Household,
    sample_profile: Profile,
    household_other_member: Profile,
) -> None:
    await _add_entry(db_session, sample_household.id, title="hh1")
    await _add_entry(db_session, sample_household.id, title="hh-read", read=True)
    await _add_entry(
        db_session, sample_household.id, profile_id=sample_profile.id, title="me"
    )
    await _add_entry(
        db_session,
        sample_household.id,
        profile_id=household_other_member.id,
        title="other",
    )
    resp = await authed_client.get(
        "/api/notifications/inbox/unread_count",
        params={"household_id": str(sample_household.id)},
    )
    assert resp.status_code == 200
    # hh1 + me. hh-read is read; "other" belongs to a different profile.
    assert resp.json()["unread"] == 2


# ── Mark-as-read actions ────────────────────────────────────────────────────


async def test_mark_inbox_entry_read(
    authed_client: AsyncClient,
    db_session: AsyncSession,
    sample_household: Household,
) -> None:
    e = await _add_entry(db_session, sample_household.id, title="x")
    resp = await authed_client.post(f"/api/notifications/inbox/{e.id}/read")
    assert resp.status_code == 200
    assert resp.json()["read_at"] is not None


async def test_cannot_mark_other_profiles_entry(
    authed_client: AsyncClient,
    db_session: AsyncSession,
    sample_household: Household,
    household_other_member: Profile,
) -> None:
    e = await _add_entry(
        db_session,
        sample_household.id,
        profile_id=household_other_member.id,
        title="theirs",
    )
    resp = await authed_client.post(f"/api/notifications/inbox/{e.id}/read")
    assert resp.status_code == 403


async def test_mark_all_read(
    authed_client: AsyncClient,
    db_session: AsyncSession,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    await _add_entry(db_session, sample_household.id, title="a")
    await _add_entry(db_session, sample_household.id, title="b")
    await _add_entry(
        db_session, sample_household.id, profile_id=sample_profile.id, title="c"
    )
    resp = await authed_client.post(
        "/api/notifications/inbox/mark_all_read",
        params={"household_id": str(sample_household.id)},
    )
    assert resp.status_code == 200
    assert resp.json()["unread"] == 0


# ── Cross-household isolation ───────────────────────────────────────────────


async def test_cannot_view_other_household_inbox(
    authed_client: AsyncClient,
    second_household: Household,
) -> None:
    resp = await authed_client.get(
        "/api/notifications/inbox", params={"household_id": str(second_household.id)}
    )
    assert resp.status_code == 403


# ── Reminder firing populates inbox ─────────────────────────────────────────


async def test_firing_reminder_creates_inbox_entry(
    authed_client: AsyncClient,
    db_session: AsyncSession,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    cal = SourceCalendar(
        household_id=sample_household.id,
        provider="manual",
        name="Family",
        color="#FF5733",
    )
    db_session.add(cal)
    await db_session.flush()
    event = Event(
        source_calendar_id=cal.id,
        external_id="evt-bell-1",
        title="Soccer Practice",
        start_time=dt.datetime.utcnow() + dt.timedelta(minutes=10),
        end_time=dt.datetime.utcnow() + dt.timedelta(minutes=70),
    )
    db_session.add(event)
    await db_session.flush()
    db_session.add(
        Reminder(
            event_id=event.id,
            household_id=sample_household.id,
            minutes_before=15,
            fire_at=dt.datetime.utcnow() - dt.timedelta(seconds=5),
        )
    )
    await db_session.flush()

    fire = await authed_client.get(
        "/api/notifications/upcoming",
        params={"household_id": str(sample_household.id)},
    )
    assert fire.status_code == 200
    assert len(fire.json()) == 1

    # Inbox should now have an entry for this reminder.
    inbox = await authed_client.get(
        "/api/notifications/inbox",
        params={"household_id": str(sample_household.id)},
    )
    titles = [e["title"] for e in inbox.json()]
    assert "Soccer Practice" in titles
