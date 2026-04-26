"""Extended list-item tests including cross-household validation."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Household, Profile, ProfileRole

pytestmark = pytest.mark.asyncio

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _create_list_and_item(
    client: AsyncClient, household_id: str
) -> tuple[str, str]:
    """Create a list with one item and return (list_id, item_id)."""
    list_resp = await client.post(
        "/api/lists",
        json={
            "household_id": household_id,
            "name": "Test List",
            "category": "todo",
        },
    )
    assert list_resp.status_code == 201
    list_id = list_resp.json()["id"]

    item_resp = await client.post(
        f"/api/lists/{list_id}/items",
        json={"text": "Test item", "sort_order": 0},
    )
    assert item_resp.status_code == 201
    item_id = item_resp.json()["id"]
    return list_id, item_id


# ── Same-household positive tests ────────────────────────────────────────────


async def test_update_item_same_household(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    list_id, item_id = await _create_list_and_item(
        authed_client, str(sample_household.id)
    )
    resp = await authed_client.put(
        f"/api/lists/{list_id}/items/{item_id}",
        json={"text": "Updated text"},
    )
    assert resp.status_code == 200
    assert resp.json()["text"] == "Updated text"


async def test_delete_item_same_household(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    list_id, item_id = await _create_list_and_item(
        authed_client, str(sample_household.id)
    )
    resp = await authed_client.delete(f"/api/lists/{list_id}/items/{item_id}")
    assert resp.status_code == 204


async def test_toggle_item_same_household(
    authed_client: AsyncClient, sample_household: Household
) -> None:
    list_id, item_id = await _create_list_and_item(
        authed_client, str(sample_household.id)
    )

    resp = await authed_client.patch(f"/api/lists/{list_id}/items/{item_id}/toggle")
    assert resp.status_code == 200
    assert resp.json()["is_checked"] is True

    resp = await authed_client.patch(f"/api/lists/{list_id}/items/{item_id}/toggle")
    assert resp.status_code == 200
    assert resp.json()["is_checked"] is False


# ── Cross-household tests ────────────────────────────────────────────────────


async def _setup_two_households(
    async_client: AsyncClient, db_session: AsyncSession
) -> tuple[str, str, str, dict]:
    """Create two households with profiles, login as household B.

    Returns (household_a_id, list_id, item_id, headers_b).
    The list+item belong to household A; headers are for household B.
    """
    # Household A + admin profile
    household_a = Household(name="Family A")
    db_session.add(household_a)
    await db_session.flush()

    profile_a = Profile(
        household_id=household_a.id,
        name="User A",
        color="#AA0000",
        role=ProfileRole.admin,
        pin_hash=_pwd.hash("1234"),
        is_active=True,
    )
    db_session.add(profile_a)
    await db_session.flush()

    # Household B + admin profile
    household_b = Household(name="Family B")
    db_session.add(household_b)
    await db_session.flush()

    profile_b = Profile(
        household_id=household_b.id,
        name="User B",
        color="#0000BB",
        role=ProfileRole.admin,
        pin_hash=_pwd.hash("5678"),
        is_active=True,
    )
    db_session.add(profile_b)
    await db_session.flush()

    # Login as profile A to create a list + item
    login_a = await async_client.post(
        "/api/auth/login",
        json={"profile_id": str(profile_a.id), "pin": "1234"},
    )
    token_a = login_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    list_resp = await async_client.post(
        "/api/lists",
        json={
            "household_id": str(household_a.id),
            "name": "A's List",
            "category": "todo",
        },
        headers=headers_a,
    )
    assert list_resp.status_code == 201
    list_id = list_resp.json()["id"]

    item_resp = await async_client.post(
        f"/api/lists/{list_id}/items",
        json={"text": "A's item", "sort_order": 0},
        headers=headers_a,
    )
    assert item_resp.status_code == 201
    item_id = item_resp.json()["id"]

    # Login as profile B
    login_b = await async_client.post(
        "/api/auth/login",
        json={"profile_id": str(profile_b.id), "pin": "5678"},
    )
    token_b = login_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    return str(household_a.id), list_id, item_id, headers_b


async def test_cross_household_item_update(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Attempt to update an item in another household's list.

    NOTE: The current implementation does not check household ownership on
    item-level endpoints (update/delete/toggle).  This test documents the
    existing behaviour — it may currently return 200 instead of 403.
    That's the bug we'll fix later.
    """
    household_a_id, list_id, item_id, headers_b = await _setup_two_households(
        async_client, db_session
    )

    resp = await async_client.put(
        f"/api/lists/{list_id}/items/{item_id}",
        json={"text": "Hacked by B"},
        headers=headers_b,
    )
    assert resp.status_code == 403


async def test_cross_household_list_access(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """A user from household B cannot list household A's lists."""
    household_a_id, _list_id, _item_id, headers_b = await _setup_two_households(
        async_client, db_session
    )

    resp = await async_client.get(
        "/api/lists",
        params={"household_id": household_a_id},
        headers=headers_b,
    )
    assert resp.status_code == 403
