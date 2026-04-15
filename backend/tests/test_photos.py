"""Tests for the photos API endpoints."""

import pytest
from httpx import AsyncClient

from app.models.user import Household, Profile


# ── Unauthenticated access ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_photos_list_requires_auth(async_client: AsyncClient, sample_household: Household):
    resp = await async_client.get("/api/photos", params={"household_id": str(sample_household.id)})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_photos_create_requires_auth(async_client: AsyncClient, sample_household: Household):
    resp = await async_client.post("/api/photos", json={
        "url": "https://example.com/photo.jpg",
        "household_id": str(sample_household.id),
    })
    assert resp.status_code == 401


# ── CRUD operations ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_photo(authed_client: AsyncClient, sample_household: Household):
    resp = await authed_client.post("/api/photos", json={
        "url": "https://example.com/family.jpg",
        "caption": "Summer vacation",
        "household_id": str(sample_household.id),
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["url"] == "https://example.com/family.jpg"
    assert data["caption"] == "Summer vacation"
    assert data["sort_order"] == 0
    assert data["household_id"] == str(sample_household.id)


@pytest.mark.asyncio
async def test_list_photos_empty(authed_client: AsyncClient, sample_household: Household):
    resp = await authed_client.get("/api/photos", params={"household_id": str(sample_household.id)})
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_photos_after_create(authed_client: AsyncClient, sample_household: Household):
    # Create two photos
    await authed_client.post("/api/photos", json={
        "url": "https://example.com/1.jpg",
        "caption": "Photo 1",
        "household_id": str(sample_household.id),
    })
    await authed_client.post("/api/photos", json={
        "url": "https://example.com/2.jpg",
        "caption": "Photo 2",
        "sort_order": 1,
        "household_id": str(sample_household.id),
    })

    resp = await authed_client.get("/api/photos", params={"household_id": str(sample_household.id)})
    assert resp.status_code == 200
    photos = resp.json()
    assert len(photos) == 2
    assert photos[0]["url"] == "https://example.com/1.jpg"
    assert photos[1]["url"] == "https://example.com/2.jpg"


@pytest.mark.asyncio
async def test_update_photo(authed_client: AsyncClient, sample_household: Household):
    resp = await authed_client.post("/api/photos", json={
        "url": "https://example.com/edit.jpg",
        "household_id": str(sample_household.id),
    })
    photo_id = resp.json()["id"]

    resp = await authed_client.put(f"/api/photos/{photo_id}", json={
        "caption": "Updated caption",
        "sort_order": 5,
    })
    assert resp.status_code == 200
    assert resp.json()["caption"] == "Updated caption"
    assert resp.json()["sort_order"] == 5


@pytest.mark.asyncio
async def test_delete_photo(authed_client: AsyncClient, sample_household: Household):
    resp = await authed_client.post("/api/photos", json={
        "url": "https://example.com/delete-me.jpg",
        "household_id": str(sample_household.id),
    })
    photo_id = resp.json()["id"]

    resp = await authed_client.delete(f"/api/photos/{photo_id}")
    assert resp.status_code == 204

    # Verify gone
    resp = await authed_client.get("/api/photos", params={"household_id": str(sample_household.id)})
    assert len(resp.json()) == 0


# ── Cross-household isolation ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_photos_cross_household_list_denied(
    authed_client: AsyncClient,
    second_household: Household,
    second_profile: Profile,
):
    resp = await authed_client.get("/api/photos", params={"household_id": str(second_household.id)})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_photos_cross_household_create_denied(
    authed_client: AsyncClient,
    second_household: Household,
    second_profile: Profile,
):
    resp = await authed_client.post("/api/photos", json={
        "url": "https://example.com/sneaky.jpg",
        "household_id": str(second_household.id),
    })
    assert resp.status_code == 403


# ── 404 handling ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_nonexistent_photo(authed_client: AsyncClient):
    resp = await authed_client.put(
        "/api/photos/00000000-0000-0000-0000-000000000000",
        json={"caption": "nope"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_photo(authed_client: AsyncClient):
    resp = await authed_client.delete("/api/photos/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
