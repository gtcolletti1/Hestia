"""Advanced notes tests — ordering, metadata, dashboard widget.

PRD refs: US-2.7.1 (notes), US-2.7.2 (dashboard integration).
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models.user import Household, Profile

pytestmark = pytest.mark.asyncio


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _create_note(
    client: AsyncClient, hid: str, pid: str, title: str, **kwargs
) -> dict:
    payload = {
        "household_id": hid,
        "author_profile_id": pid,
        "title": title,
        "body": kwargs.pop("body", ""),
        **kwargs,
    }
    resp = await client.post("/api/notes", json=payload)
    assert resp.status_code == 201
    return resp.json()


# ── Tests ────────────────────────────────────────────────────────────────────


async def test_note_has_timestamps(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """Notes include created_at and updated_at."""
    note = await _create_note(
        authed_client,
        str(sample_household.id),
        str(sample_profile.id),
        "Timestamp Test",
    )
    assert "created_at" in note
    assert "updated_at" in note


async def test_note_color_default(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """Notes default to a yellow color when not specified."""
    note = await _create_note(
        authed_client,
        str(sample_household.id),
        str(sample_profile.id),
        "Default Color",
    )
    assert note["color"] == "#FBBF24"


async def test_note_custom_color(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """Notes accept a custom color."""
    note = await _create_note(
        authed_client,
        str(sample_household.id),
        str(sample_profile.id),
        "Custom Color",
        color="#EF4444",
    )
    assert note["color"] == "#EF4444"


async def test_pinned_notes_appear_first(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """Pinned notes sort before unpinned notes."""
    hid = str(sample_household.id)
    pid = str(sample_profile.id)

    await _create_note(authed_client, hid, pid, "Not Pinned 1")
    await _create_note(authed_client, hid, pid, "Pinned One", pinned=True)
    await _create_note(authed_client, hid, pid, "Not Pinned 2")

    resp = await authed_client.get(
        "/api/notes", params={"household_id": hid}
    )
    notes = resp.json()
    assert notes[0]["title"] == "Pinned One"
    assert notes[0]["pinned"] is True


async def test_update_note_preserves_author(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """Updating a note's title doesn't change the author."""
    hid = str(sample_household.id)
    pid = str(sample_profile.id)

    note = await _create_note(authed_client, hid, pid, "Original Title")

    resp = await authed_client.put(
        f"/api/notes/{note['id']}",
        json={"title": "Updated Title"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"
    assert resp.json()["author_profile_id"] == pid


async def test_delete_note(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """Deleting a note returns 204."""
    hid = str(sample_household.id)
    pid = str(sample_profile.id)

    note = await _create_note(authed_client, hid, pid, "Delete Me")

    resp = await authed_client.delete(f"/api/notes/{note['id']}")
    assert resp.status_code == 204
