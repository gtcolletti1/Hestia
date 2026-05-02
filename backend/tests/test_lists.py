"""Tests for the lists (task lists / items) API."""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.list import ListCategory, TaskList
from app.models.user import Household, Profile

pytestmark = pytest.mark.asyncio


# ── Helpers ──────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture()
async def task_list(
    authed_client: AsyncClient, sample_household: Household
) -> dict:
    """Create a task list via API and return the response body."""
    resp = await authed_client.post(
        "/api/lists",
        json={
            "household_id": str(sample_household.id),
            "name": "Groceries",
            "category": "grocery",
            "icon": "🛒",
        },
    )
    assert resp.status_code == 201
    return resp.json()


# ── Tests ────────────────────────────────────────────────────────────────────


async def test_create_list(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    resp = await authed_client.post(
        "/api/lists",
        json={
            "household_id": str(sample_household.id),
            "name": "Packing List",
            "category": "packing",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Packing List"
    assert body["category"] == "packing"
    assert body["household_id"] == str(sample_household.id)
    assert body["item_count"] == 0


async def test_add_item(
    authed_client: AsyncClient, task_list: dict
) -> None:
    list_id = task_list["id"]
    resp = await authed_client.post(
        f"/api/lists/{list_id}/items",
        json={"text": "Milk", "sort_order": 0},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["text"] == "Milk"
    assert body["is_checked"] is False
    assert body["list_id"] == list_id


async def test_toggle_item(
    authed_client: AsyncClient, task_list: dict
) -> None:
    list_id = task_list["id"]

    # Add an item
    item_resp = await authed_client.post(
        f"/api/lists/{list_id}/items",
        json={"text": "Eggs", "sort_order": 0},
    )
    item_id = item_resp.json()["id"]

    # Toggle it on
    resp = await authed_client.patch(f"/api/lists/{list_id}/items/{item_id}/toggle")
    assert resp.status_code == 200
    assert resp.json()["is_checked"] is True

    # Toggle it off
    resp = await authed_client.patch(f"/api/lists/{list_id}/items/{item_id}/toggle")
    assert resp.status_code == 200
    assert resp.json()["is_checked"] is False


async def test_reorder_items(
    authed_client: AsyncClient, task_list: dict
) -> None:
    list_id = task_list["id"]

    # Add three items
    ids = []
    for i, text in enumerate(["Apple", "Banana", "Cherry"]):
        r = await authed_client.post(
            f"/api/lists/{list_id}/items",
            json={"text": text, "sort_order": i},
        )
        ids.append(r.json()["id"])

    # Reverse the order
    reversed_ids = list(reversed(ids))
    resp = await authed_client.put(
        f"/api/lists/{list_id}/reorder",
        json={"item_ids": reversed_ids},
    )
    assert resp.status_code == 200
    returned_ids = [item["id"] for item in resp.json()]
    assert returned_ids[:3] == reversed_ids


async def test_delete_item(
    authed_client: AsyncClient, task_list: dict
) -> None:
    list_id = task_list["id"]

    item_resp = await authed_client.post(
        f"/api/lists/{list_id}/items",
        json={"text": "Butter", "sort_order": 0},
    )
    item_id = item_resp.json()["id"]

    resp = await authed_client.delete(f"/api/lists/{list_id}/items/{item_id}")
    assert resp.status_code == 204


# ── Bug 2 regression: 'other' category works; shopping/chores are rejected ──


async def test_create_list_with_other_category(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    """Category 'other' is now a valid backend value (was rejected before)."""
    resp = await authed_client.post(
        "/api/lists",
        json={
            "household_id": str(sample_household.id),
            "name": "Misc",
            "category": "other",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["category"] == "other"
    assert body["name"] == "Misc"


async def test_shopping_and_chores_categories_are_rejected(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    """The removed UI categories 'shopping' and 'chores' must be rejected."""
    for bad in ("shopping", "chores"):
        resp = await authed_client.post(
            "/api/lists",
            json={
                "household_id": str(sample_household.id),
                "name": f"Should fail: {bad}",
                "category": bad,
            },
        )
        assert resp.status_code == 422, f"expected 422 for category={bad}, got {resp.status_code}: {resp.text}"
