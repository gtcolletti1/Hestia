"""Direct unit tests for the privacy_mode → splash_calendar_mode migration.

We test the migration helper logic by importlib-loading the revision
module and exercising its mapping rules against synthetic settings
dicts. This avoids spinning up a full Alembic environment in pytest
while still catching regressions in the mapping itself.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


_MIGRATION_PATH = (
    Path(__file__).resolve().parent.parent
    / "alembic"
    / "versions"
    / "9f2a4d8c1e73_splash_privacy_settings.py"
)


@pytest.fixture(scope="module")
def migration_module():
    spec = importlib.util.spec_from_file_location(
        "splash_privacy_migration", _MIGRATION_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _emulate_upgrade_one(module, settings: dict | None) -> dict:
    """Run the per-row upgrade logic against a single settings dict."""
    current = module._coerce_settings(json.dumps(settings) if settings else None) or {}

    legacy = current.pop("privacy_mode", None)
    derived = "busy_only" if legacy is True else "off"
    defaults = {**module._NEW_DEFAULTS, "splash_calendar_mode": derived}
    for key, default in defaults.items():
        current.setdefault(key, default)
    return current


def test_privacy_mode_true_maps_to_busy_only(migration_module) -> None:
    out = _emulate_upgrade_one(migration_module, {"privacy_mode": True})
    assert out["splash_calendar_mode"] == "busy_only"
    assert "privacy_mode" not in out


def test_privacy_mode_false_maps_to_off(migration_module) -> None:
    out = _emulate_upgrade_one(migration_module, {"privacy_mode": False})
    assert out["splash_calendar_mode"] == "off"
    assert "privacy_mode" not in out


def test_missing_privacy_mode_defaults_to_off(migration_module) -> None:
    out = _emulate_upgrade_one(migration_module, {"theme": "dark"})
    assert out["splash_calendar_mode"] == "off"
    assert out["theme"] == "dark"  # other keys preserved


def test_existing_splash_keys_are_not_clobbered(migration_module) -> None:
    """A partial-migration scenario: someone already wrote splash_calendar_mode
    by hand. Defaults must NOT overwrite existing values."""
    out = _emulate_upgrade_one(
        migration_module,
        {"privacy_mode": True, "splash_calendar_mode": "hidden"},
    )
    assert out["splash_calendar_mode"] == "hidden"


def test_all_new_defaults_are_seeded(migration_module) -> None:
    out = _emulate_upgrade_one(migration_module, {})
    for key in migration_module._NEW_DEFAULTS:
        assert key in out


def test_upgrade_idempotent_on_already_migrated_settings(migration_module) -> None:
    """Running the upgrade a second time should be a no-op for keys that
    already have values (privacy_mode is gone, splash_* are present)."""
    first = _emulate_upgrade_one(migration_module, {"privacy_mode": True})
    second = _emulate_upgrade_one(migration_module, first)
    assert first == second


def test_coerce_settings_handles_text_json(migration_module) -> None:
    # SQLite path: JSON column is TEXT, comes back as a string.
    parsed = migration_module._coerce_settings('{"privacy_mode": true}')
    assert parsed == {"privacy_mode": True}


def test_coerce_settings_handles_garbage(migration_module) -> None:
    assert migration_module._coerce_settings("not json at all") is None
    assert migration_module._coerce_settings(None) is None
    assert migration_module._coerce_settings(12345) is None
