"""CalDAV / iCal subscription integration using httpx.

For full iCalendar (RFC 5545) parsing in production, install the
``icalendar`` package:  pip install icalendar
The helpers below implement a lightweight manual parser sufficient for
common VEVENT properties.
"""


import logging
import re
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2


class CalDAVClient:
    """Read/write client for CalDAV servers."""

    def __init__(
        self,
        url: str,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        auth = (username, password) if username and password else None
        self._client = httpx.AsyncClient(
            base_url=url,
            auth=auth,
            timeout=30.0,
        )
        self.url = url

    async def close(self) -> None:
        await self._client.aclose()

    async def _request_with_retry(
        self,
        method: str,
        url: str = "",
        **kwargs: Any,
    ) -> httpx.Response:
        import asyncio

        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                resp = await self._client.request(method, url, **kwargs)
                if resp.status_code == 429 or resp.status_code >= 500:
                    wait = RETRY_BACKOFF_BASE ** attempt
                    logger.warning(
                        "CalDAV %s %s returned %s, retrying in %ss",
                        method, url, resp.status_code, wait,
                    )
                    await asyncio.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp
            except httpx.HTTPStatusError:
                raise
            except httpx.HTTPError as exc:
                last_exc = exc
                wait = RETRY_BACKOFF_BASE ** attempt
                logger.warning("CalDAV request error: %s, retrying in %ss", exc, wait)
                await asyncio.sleep(wait)

        raise last_exc or RuntimeError("CalDAV request failed after retries")

    async def fetch_events(
        self, start: datetime, end: datetime
    ) -> list[dict]:
        """Fetch events from a CalDAV server using a REPORT request.

        Falls back to a simple GET if the server does not support REPORT.
        """
        # Build a CalDAV calendar-query REPORT body
        report_body = _build_calendar_query_xml(start, end)

        try:
            resp = await self._request_with_retry(
                "REPORT",
                "",
                content=report_body,
                headers={
                    "Content-Type": "application/xml; charset=utf-8",
                    "Depth": "1",
                },
            )
            return _parse_multistatus_ical(resp.text)
        except httpx.HTTPStatusError:
            # Fallback: simple GET (some servers expose .ics directly)
            logger.info("REPORT not supported, falling back to GET")
            resp = await self._request_with_retry("GET", "")
            return parse_ical_text(resp.text)

    async def put_event(self, path: str, ical_text: str) -> None:
        """Create or update an event via PUT (read/write CalDAV)."""
        await self._request_with_retry(
            "PUT",
            path,
            content=ical_text,
            headers={"Content-Type": "text/calendar; charset=utf-8"},
        )

    async def delete_event(self, path: str) -> None:
        """Delete an event via DELETE (read/write CalDAV)."""
        await self._request_with_retry("DELETE", path)


class ICalSubscription:
    """Read-only iCal (.ics URL) subscription handler."""

    async def fetch_and_parse(self, ical_url: str) -> list[dict]:
        """GET an .ics URL and parse all VEVENTs into local event dicts."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(ical_url)
            resp.raise_for_status()
            return parse_ical_text(resp.text)


# ── iCalendar parsing helpers ────────────────────────────────────────────────


def parse_ical_text(text: str) -> list[dict]:
    """Parse raw iCalendar text and extract VEVENT blocks into dicts.

    This is a lightweight parser for the most common VEVENT properties.
    For production use, consider the ``icalendar`` package for full
    RFC 5545 compliance.
    """
    events: list[dict] = []
    in_event = False
    current: dict[str, str] = {}
    current_params: dict[str, dict[str, str]] = {}

    for line in _unfold_lines(text):
        if line.strip() == "BEGIN:VEVENT":
            in_event = True
            current = {}
            current_params = {}
        elif line.strip() == "END:VEVENT" and in_event:
            in_event = False
            events.append(_vevent_dict_to_local(current, current_params))
        elif in_event:
            key, _, value = line.partition(":")
            parts = key.split(";")
            base_key = parts[0].strip().upper()
            params: dict[str, str] = {}
            for p in parts[1:]:
                pk, _, pv = p.partition("=")
                params[pk.strip().upper()] = pv.strip()
            current[base_key] = value.strip()
            current_params[base_key] = params

    return events


def _unfold_lines(text: str) -> list[str]:
    """Handle RFC 5545 line unfolding (continuation lines start with space/tab)."""
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").split("\n"):
        if raw.startswith((" ", "\t")) and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    return lines


def _vevent_dict_to_local(
    props: dict[str, str],
    params: dict[str, dict[str, str]] | None = None,
) -> dict:
    """Convert a parsed VEVENT property dict to a local event dict."""
    params = params or {}
    start_raw = props.get("DTSTART", "")
    end_raw = props.get("DTEND", "")
    all_day = len(start_raw) == 8  # YYYYMMDD format

    start_tz = params.get("DTSTART", {}).get("TZID")
    end_tz = params.get("DTEND", {}).get("TZID") or start_tz

    start_time = _parse_ical_datetime(start_raw, start_tz)
    end_time = _parse_ical_datetime(end_raw, end_tz) if end_raw else start_time

    return {
        "external_id": props.get("UID"),
        "title": props.get("SUMMARY", "(No title)"),
        "description": props.get("DESCRIPTION"),
        "location": props.get("LOCATION"),
        "start_time": start_time,
        "end_time": end_time,
        "all_day": all_day,
        "recurrence_rule": props.get("RRULE"),
        "is_private": props.get("CLASS", "").upper() == "PRIVATE",
    }


def _parse_ical_datetime(raw: str, tzid: str | None = None) -> datetime:
    """Parse an iCalendar date or datetime string.

    Handles three forms per RFC 5545:
      * Date only (YYYYMMDD) — returned as midnight UTC
      * UTC datetime (YYYYMMDDTHHmmSSZ)
      * Floating / TZID-tagged datetime (YYYYMMDDTHHmmSS) — interpreted in
        the supplied tzid (e.g. ``America/New_York``) and converted to UTC.
        Without a tzid, treated as UTC for backwards compatibility.
    """
    raw = raw.strip()
    if not raw:
        return datetime.now(timezone.utc)

    # Date only: YYYYMMDD (all-day event)
    if len(raw) == 8 and raw.isdigit():
        return datetime.strptime(raw, "%Y%m%d").replace(tzinfo=timezone.utc)

    # UTC datetime: YYYYMMDDTHHmmSSZ
    if raw.endswith("Z"):
        return datetime.strptime(raw, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)

    # Floating / local datetime: YYYYMMDDTHHmmSS
    if "T" in raw:
        naive = datetime.strptime(raw, "%Y%m%dT%H%M%S")
        if tzid:
            try:
                local = naive.replace(tzinfo=ZoneInfo(tzid))
                return local.astimezone(timezone.utc)
            except ZoneInfoNotFoundError:
                logger.warning("Unknown TZID %s, falling back to UTC", tzid)
        return naive.replace(tzinfo=timezone.utc)

    return datetime.now(timezone.utc)


# ── CalDAV XML helpers ───────────────────────────────────────────────────────


def _build_calendar_query_xml(start: datetime, end: datetime) -> str:
    """Build a CalDAV calendar-query REPORT XML body."""
    start_str = start.strftime("%Y%m%dT%H%M%SZ")
    end_str = end.strftime("%Y%m%dT%H%M%SZ")
    return (
        '<?xml version="1.0" encoding="utf-8" ?>'
        '<C:calendar-query xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">'
        "<D:prop><D:getetag/><C:calendar-data/></D:prop>"
        "<C:filter><C:comp-filter name=\"VCALENDAR\">"
        "<C:comp-filter name=\"VEVENT\">"
        f'<C:time-range start="{start_str}" end="{end_str}"/>'
        "</C:comp-filter></C:comp-filter></C:filter>"
        "</C:calendar-query>"
    )


def _parse_multistatus_ical(xml_text: str) -> list[dict]:
    """Extract iCalendar data from a CalDAV multistatus XML response.

    Uses a simple regex approach to extract calendar-data content.
    For production, consider an XML parser like lxml.
    """
    events: list[dict] = []
    # Match content within <cal:calendar-data> or <C:calendar-data> tags
    pattern = re.compile(
        r"<(?:cal|C):calendar-data[^>]*>(.*?)</(?:cal|C):calendar-data>",
        re.DOTALL,
    )
    for match in pattern.finditer(xml_text):
        ical_text = match.group(1)
        events.extend(parse_ical_text(ical_text))
    return events
