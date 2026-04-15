"""Tests for the notes (message board) API endpoints."""

import pytest
from httpx import AsyncClient

from app.models.user import Household, Profile


# ── Unauthenticated access ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_notes_list_requires_auth(async_client: AsyncClient, sample_household: Household):
    resp = await async_client.get("/api/notes", params={"household_id": str(sample_household.id)})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_notes_create_requires_auth(async_client: AsyncClient, sample_household: Household):
    resp = await async_client.post("/api/notes", json={
        "title": "Test",
        "household_id": str(sample_household.id),
    })
    assert resp.status_code == 401


# ── CRUD operations ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_note(authed_client: AsyncClient, sample_household: Household, sample_profile: Profile):
    resp = await authed_client.post("/api/notes", json={
        "title": "Grocery reminder",
        "body": "Don't forget milk!",
        "color": "#34D399",
        "household_id": str(sample_household.id),
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Grocery reminder"
    assert data["body"] == "Don't forget milk!"
    assert data["color"] == "#34D399"
    assert data["pinned"] is False
    assert data["author_profile_id"] == str(sample_profile.id)
    assert data["household_id"] == str(sample_household.id)


@pytest.mark.asyncio
async def test_list_notes_empty(authed_client: AsyncClient, sample_household: Household):
    resp = await authed_client.get("/api/notes", params={"household_id": str(sample_household.id)})
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_notes_pinned_first(authed_client: AsyncClient, sample_household: Household):
    # Create unpinned then pinned
    await authed_client.post("/api/notes", json={
        "title": "Regular note",
        "household_id": str(sample_household.id),
    })
    await authed_client.post("/api/notes", json={
        "title": "Pinned note",
        "pinned": True,
        "household_id": str(sample_household.id),
    })

    resp = await authed_client.get("/api/notes", params={"household_id": str(sample_household.id)})
    notes = resp.json()
    assert len(notes) == 2
    assert notes[0]["title"] == "Pinned note"
    assert notes[0]["pinned"] is True
    assert notes[1]["title"] == "Regular note"


@pytest.mark.asyncio
async def test_update_note(authed_client: AsyncClient, sample_household: Household):
    resp = await authed_client.post("/api/notes", json={
        "title": "Original",
        "body": "Original body",
        "household_id": str(sample_household.id),
    })
    note_id = resp.json()["id"]

    resp = await authed_client.put(f"/api/notes/{note_id}", json={
        "title": "Updated",
        "pinned": True,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Updated"
    assert data["body"] == "Original body"  # unchanged
    assert data["pinned"] is True


@pytest.mark.asyncio
async def test_delete_note(authed_client: AsyncClient, sample_household: Household):
    resp = await authed_client.post("/api/notes", json={
        "title": "Delete me",
        "household_id": str(sample_household.id),
    })
    note_id = resp.json()["id"]

    resp = await authed_client.delete(f"/api/notes/{note_id}")
    assert resp.status_code == 204

    # Verify gone
    resp = await authed_client.get("/api/notes", params={"household_id": str(sample_household.id)})
    assert len(resp.json()) == 0


# ── Cross-household isolation ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_notes_cross_household_list_denied(
    authed_client: AsyncClient,
    second_household: Household,
    second_profile: Profile,
):
    resp = await authed_client.get("/api/notes", params={"household_id": str(second_household.id)})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_notes_cross_household_create_denied(
    authed_client: AsyncClient,
    second_household: Household,
    second_profile: Profile,
):
    resp = await authed_client.post("/api/notes", json={
        "title": "Sneaky note",
        "household_id": str(second_household.id),
    })
    assert resp.status_code == 403


# ── 404 handling ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_nonexistent_note(authed_client: AsyncClient):
    resp = await authed_client.put(
        "/api/notes/00000000-0000-0000-0000-000000000000",
        json={"title": "nope"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_note(authed_client: AsyncClient):
    resp = await authed_client.delete("/api/notes/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
