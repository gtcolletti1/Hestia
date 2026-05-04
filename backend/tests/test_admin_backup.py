"""Tests for /api/admin/export and /api/admin/import (JSON backup/restore)."""
from __future__ import annotations

from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.list import ListCategory, ListItem, TaskList
from app.models.routine import Routine, RoutineStep, TimeBlock
from app.models.school_closure import SchoolClosure
from app.models.user import Household, Profile

pytestmark = pytest.mark.asyncio


async def _seed_some_data(db: AsyncSession, household: Household, admin: Profile) -> None:
    """Add a routine + step, a list + items, and a school closure."""
    routine = Routine(
        household_id=household.id,
        name="Morning",
        time_block=TimeBlock.morning,
        days_of_week=[0, 1, 2, 3, 4],
        is_active=True,
    )
    db.add(routine)
    await db.flush()
    db.add(
        RoutineStep(
            routine_id=routine.id,
            label="Brush teeth",
            sort_order=0,
            points_value=5,
            school_day_only=False,
        )
    )
    db.add(
        RoutineStep(
            routine_id=routine.id,
            label="Pack backpack",
            sort_order=1,
            points_value=3,
            school_day_only=True,
        )
    )

    tlist = TaskList(
        household_id=household.id,
        name="Groceries",
        category=ListCategory.grocery,
        sort_order=0,
    )
    db.add(tlist)
    await db.flush()
    db.add(ListItem(list_id=tlist.id, text="Milk", sort_order=0))
    db.add(ListItem(list_id=tlist.id, text="Eggs", sort_order=1))

    db.add(
        SchoolClosure(
            household_id=household.id,
            date=date(2026, 1, 5),
            reason="Snow day",
            created_by_profile_id=admin.id,
        )
    )
    await db.flush()


async def test_export_returns_versioned_payload(
    authed_client: AsyncClient,
    db_session: AsyncSession,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    await _seed_some_data(db_session, sample_household, sample_profile)
    await db_session.commit()

    resp = await authed_client.get("/api/admin/export")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["version"] == 1
    assert "exported_at" in body
    assert body["household"]["name"] == "Test Family"

    assert len(body["routines"]) == 1
    assert len(body["routine_steps"]) == 2
    step_labels = {s["label"] for s in body["routine_steps"]}
    assert step_labels == {"Brush teeth", "Pack backpack"}

    assert len(body["task_lists"]) == 1
    assert len(body["list_items"]) == 2
    assert len(body["school_closures"]) == 1
    assert body["school_closures"][0]["reason"] == "Snow day"

    # The admin profile fixture should round-trip
    assert any(p["name"] == "Admin User" for p in body["profiles"])


async def test_import_replaces_household_data(
    authed_client: AsyncClient,
    db_session: AsyncSession,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    # Seed initial data + take a snapshot.
    await _seed_some_data(db_session, sample_household, sample_profile)
    await db_session.commit()

    snapshot = (await authed_client.get("/api/admin/export")).json()

    # Mutate live data (delete the lists, change household name).
    await db_session.execute(
        ListItem.__table__.delete().where(
            ListItem.list_id.in_(select(TaskList.id).where(TaskList.household_id == sample_household.id))
        )
    )
    await db_session.execute(TaskList.__table__.delete().where(TaskList.household_id == sample_household.id))
    sample_household.name = "Mutated"
    await db_session.commit()

    # Restore the snapshot.
    resp = await authed_client.post("/api/admin/import", json=snapshot)
    assert resp.status_code == 200, resp.text
    counts = resp.json()["restored"]
    assert counts["task_lists"] == 1
    assert counts["list_items"] == 2
    assert counts["routine_steps"] == 2

    # Verify state was restored.
    await db_session.refresh(sample_household)
    assert sample_household.name == "Test Family"

    items = (
        await db_session.execute(
            select(ListItem).join(TaskList).where(TaskList.household_id == sample_household.id)
        )
    ).scalars().all()
    assert {i.text for i in items} == {"Milk", "Eggs"}


async def test_import_rejects_unknown_version(
    authed_client: AsyncClient,
) -> None:
    resp = await authed_client.post("/api/admin/import", json={"version": 999})
    assert resp.status_code == 400
    assert "version" in resp.json()["detail"].lower()


async def test_import_forces_household_id_to_caller(
    authed_client: AsyncClient,
    db_session: AsyncSession,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """A backup that claims rows belong to a different household must still be
    inserted under the caller's household — prevents cross-household injection."""
    await _seed_some_data(db_session, sample_household, sample_profile)
    await db_session.commit()
    snapshot = (await authed_client.get("/api/admin/export")).json()

    # Tamper: pretend the routines belong elsewhere.
    bogus_id = "00000000-0000-0000-0000-000000000099"
    for r in snapshot["routines"]:
        r["household_id"] = bogus_id

    resp = await authed_client.post("/api/admin/import", json=snapshot)
    assert resp.status_code == 200, resp.text

    # Routines must still belong to the caller's household.
    routines = (
        await db_session.execute(select(Routine).where(Routine.household_id == sample_household.id))
    ).scalars().all()
    assert len(routines) == 1
