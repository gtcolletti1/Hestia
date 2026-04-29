"""Tests for the routine templates endpoint."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.data.routine_templates import ROUTINE_TEMPLATES
from app.models.user import Household, Profile

pytestmark = pytest.mark.asyncio


async def test_list_templates_requires_auth(async_client: AsyncClient) -> None:
    resp = await async_client.get("/api/routines/templates")
    assert resp.status_code == 401


async def test_list_templates_returns_curated_set(authed_client: AsyncClient) -> None:
    resp = await authed_client.get("/api/routines/templates")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) == len(ROUTINE_TEMPLATES) == 4

    expected_ids = {t["id"] for t in ROUTINE_TEMPLATES}
    assert {t["id"] for t in body} == expected_ids
    assert expected_ids == {
        "morning-routine",
        "after-school-routine",
        "bedtime-routine",
        "tidy-up",
    }

    for tpl in body:
        for field in ("id", "name", "description", "icon", "time_block",
                      "days_of_week", "steps"):
            assert field in tpl
        assert tpl["time_block"] in {"morning", "afternoon", "evening", "bedtime"}
        assert isinstance(tpl["days_of_week"], list)
        assert all(0 <= d <= 6 for d in tpl["days_of_week"])
        assert len(tpl["steps"]) >= 1
        for step in tpl["steps"]:
            assert step["label"]
            assert "points_value" in step


async def test_templates_path_not_treated_as_routine_id(
    authed_client: AsyncClient,
) -> None:
    """Regression: /routines/templates must resolve before /routines/{id}.

    If route ordering were wrong, FastAPI would try to coerce the literal
    string 'templates' into a UUID and respond with 422.
    """
    resp = await authed_client.get("/api/routines/templates")
    assert resp.status_code == 200, resp.text


async def test_each_template_creates_a_valid_routine(
    authed_client: AsyncClient,
    sample_household: Household,
    sample_profile: Profile,
) -> None:
    """Every template payload must be schema-compatible with POST /routines."""
    resp = await authed_client.get("/api/routines/templates")
    assert resp.status_code == 200
    templates = resp.json()

    for tpl in templates:
        payload = {
            "household_id": str(sample_household.id),
            "profile_id": str(sample_profile.id),
            "name": tpl["name"],
            "time_block": tpl["time_block"],
            "days_of_week": tpl["days_of_week"],
            "steps": [
                {
                    "label": s["label"],
                    "icon": s.get("icon"),
                    "points_value": s.get("points_value", 0),
                    "sort_order": i,
                }
                for i, s in enumerate(tpl["steps"])
            ],
        }
        create = await authed_client.post("/api/routines", json=payload)
        assert create.status_code == 201, (
            f"template {tpl['id']} failed: {create.status_code} {create.text}"
        )
        body = create.json()
        assert body["name"] == tpl["name"]
        assert len(body["steps"]) == len(tpl["steps"])
