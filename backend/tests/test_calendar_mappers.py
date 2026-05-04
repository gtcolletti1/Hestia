"""Mapping tests for Google + Outlook calendar integrations.

The dashboard/splash agenda dedup relies on instance overrides being
persisted with ``master_external_id`` and ``recurrence_id`` so the
shared expansion helper can skip the master's natural occurrence at
that slot. Verify the mappers actually populate those fields.
"""
from datetime import datetime, timezone

from app.integrations.google_calendar import map_google_event_to_local
from app.integrations.outlook_calendar import map_outlook_event_to_local


# ── Google ──────────────────────────────────────────────────────────────────


def test_google_master_sets_self_as_master_external_id():
    payload = {
        "id": "abc123",
        "summary": "Weekly",
        "start": {"dateTime": "2026-05-06T18:00:00Z", "timeZone": "America/New_York"},
        "end": {"dateTime": "2026-05-06T19:00:00Z", "timeZone": "America/New_York"},
        "recurrence": ["RRULE:FREQ=WEEKLY"],
    }
    out = map_google_event_to_local(payload)
    assert out["external_id"] == "abc123"
    assert out["master_external_id"] == "abc123"
    assert out["recurrence_rule"] == "RRULE:FREQ=WEEKLY"
    assert out["recurrence_id"] is None
    assert out["start_tzid"] == "America/New_York"


def test_google_modified_instance_carries_override_fields():
    payload = {
        "id": "abc123_20260513T180000Z",
        "recurringEventId": "abc123",
        "originalStartTime": {"dateTime": "2026-05-13T18:00:00Z"},
        "summary": "Weekly",
        "location": "Backyard",
        "start": {"dateTime": "2026-05-13T18:00:00Z"},
        "end": {"dateTime": "2026-05-13T19:00:00Z"},
    }
    out = map_google_event_to_local(payload)
    assert out["master_external_id"] == "abc123"
    assert out["recurrence_id"] == datetime(2026, 5, 13, 18, 0, tzinfo=timezone.utc)
    assert out["location"] == "Backyard"


def test_google_exdates_parsed_from_recurrence_array():
    payload = {
        "id": "abc",
        "summary": "Weekly w/ skip",
        "start": {"dateTime": "2026-05-06T18:00:00Z"},
        "end": {"dateTime": "2026-05-06T19:00:00Z"},
        "recurrence": [
            "RRULE:FREQ=WEEKLY;COUNT=3",
            "EXDATE;TZID=America/New_York:20260513T140000",
        ],
    }
    out = map_google_event_to_local(payload)
    assert out["recurrence_rule"] == "RRULE:FREQ=WEEKLY;COUNT=3"
    # 14:00 New_York on 2026-05-13 == 18:00 UTC (EDT)
    assert out["exdates"] is not None
    parsed = datetime.fromisoformat(out["exdates"])
    assert parsed == datetime(2026, 5, 13, 18, 0, tzinfo=timezone.utc)


def test_google_single_event_has_no_master_or_recurrence_id():
    payload = {
        "id": "single",
        "summary": "One-off",
        "start": {"dateTime": "2026-05-01T10:00:00Z"},
        "end": {"dateTime": "2026-05-01T11:00:00Z"},
    }
    out = map_google_event_to_local(payload)
    assert out["master_external_id"] is None
    assert out["recurrence_id"] is None
    assert out["recurrence_rule"] is None


# ── Outlook ─────────────────────────────────────────────────────────────────


def test_outlook_master_sets_self_as_master_external_id():
    payload = {
        "id": "AAMkA-master",
        "subject": "Weekly Sync",
        "isAllDay": False,
        "start": {"dateTime": "2026-05-06T18:00:00.0000000", "timeZone": "UTC"},
        "end": {"dateTime": "2026-05-06T19:00:00.0000000", "timeZone": "UTC"},
        "recurrence": {
            "pattern": {"type": "weekly", "interval": 1, "daysOfWeek": ["wednesday"]},
        },
    }
    out = map_outlook_event_to_local(payload)
    assert out["external_id"] == "AAMkA-master"
    assert out["master_external_id"] == "AAMkA-master"
    assert out["recurrence_id"] is None


def test_outlook_exception_carries_override_fields():
    payload = {
        "id": "AAMkA-exception",
        "seriesMasterId": "AAMkA-master",
        "originalStart": "2026-05-13T18:00:00Z",
        "subject": "Weekly Sync",
        "isAllDay": False,
        "start": {"dateTime": "2026-05-13T19:00:00.0000000", "timeZone": "UTC"},
        "end": {"dateTime": "2026-05-13T20:00:00.0000000", "timeZone": "UTC"},
    }
    out = map_outlook_event_to_local(payload)
    assert out["master_external_id"] == "AAMkA-master"
    assert out["recurrence_id"] == datetime(2026, 5, 13, 18, 0, tzinfo=timezone.utc)
