"""Advanced list tests — archival, assigned profiles, due dates, fast entry.

PRD refs: US-2.5.1 (archival), US-2.5.2 (item features), US-2.5.3 (touch).
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models.user import Household, Profile

pytestmark = pytest.mark.asyncio


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _create_list(client: AsyncClient, hid: str, name: str, **kwargs) -> dict:
    resp = await client.post(
        "/api/lists",
        json={"household_id": hid, "name": name, "category": "todo", **kwargs},
    )
    assert resp.status_code == 201
    return resp.json()


# ── Tests ────────────────────────────────────────────────────────────────────


async def test_archive_list(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    """Archiving a list sets is_archived=True."""
    hid = str(sample_household.id)
    lst = await _create_list(authed_client, hid, "Archive Test")

    resp = await authed_client.put(
        f"/api/lists/{lst['id']}",
        json={"is_archived": True},
    )
    assert resp.status_code == 200
    assert resp.json()["is_archived"] is True


async def test_archived_list_excluded_from_dashboard(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    """Archived lists don't appear in the dashboard's active_lists."""
    hid = str(sample_household.id)
    lst = await _create_list(authed_client, hid, "Hidden List")

    # Archive it
    await authed_client.put(f"/api/lists/{lst['id']}", json={"is_archived": True})

    # Dashboard should not include it
    resp = await authed_client.get(
        "/api/dashboard", params={"household_id": hid}
    )
    list_names = [al["name"] for al in resp.json()["active_lists"]]
    assert "Hidden List" not in list_names


async def test_list_item_with_assigned_profile(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """List items can have an assigned_profile_id."""
    hid = str(sample_household.id)
    pid = str(sample_profile.id)
    lst = await _create_list(authed_client, hid, "Chore List")

    resp = await authed_client.post(
        f"/api/lists/{lst['id']}/items",
        json={"text": "Take out trash", "sort_order": 0, "assigned_profile_id": pid},
    )
    assert resp.status_code == 201
    assert resp.json()["assigned_profile_id"] == pid


async def test_list_item_with_due_date(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    """List items can have an optional due_date."""
    hid = str(sample_household.id)
    lst = await _create_list(authed_client, hid, "Due Date List")

    resp = await authed_client.post(
        f"/api/lists/{lst['id']}/items",
        json={"text": "Buy milk", "sort_order": 0, "due_date": "2024-12-25"},
    )
    assert resp.status_code == 201
    assert resp.json()["due_date"] == "2024-12-25"


async def test_list_item_toggle_checked(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    """PATCH toggle flips is_checked and flipping again unsets it."""
    hid = str(sample_household.id)
    lst = await _create_list(authed_client, hid, "Toggle List")

    item_resp = await authed_client.post(
        f"/api/lists/{lst['id']}/items",
        json={"text": "Check me", "sort_order": 0},
    )
    item_id = item_resp.json()["id"]
    assert item_resp.json()["is_checked"] is False

    # Check
    resp = await authed_client.patch(f"/api/lists/{lst['id']}/items/{item_id}/toggle")
    assert resp.json()["is_checked"] is True

    # Uncheck
    resp = await authed_client.patch(f"/api/lists/{lst['id']}/items/{item_id}/toggle")
    assert resp.json()["is_checked"] is False


async def test_list_with_category(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    """Lists can be created with different categories."""
    hid = str(sample_household.id)
    for cat in ("grocery", "packing", "school", "errands"):
        resp = await authed_client.post(
            "/api/lists",
            json={"household_id": hid, "name": f"{cat} list", "category": cat},
        )
        assert resp.status_code == 201
        assert resp.json()["category"] == cat


async def test_delete_list_item(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    """Deleting a list item removes it."""
    hid = str(sample_household.id)
    lst = await _create_list(authed_client, hid, "Delete Item List")

    item = await authed_client.post(
        f"/api/lists/{lst['id']}/items",
        json={"text": "Remove me", "sort_order": 0},
    )
    item_id = item.json()["id"]

    resp = await authed_client.delete(f"/api/lists/{lst['id']}/items/{item_id}")
    assert resp.status_code == 204
