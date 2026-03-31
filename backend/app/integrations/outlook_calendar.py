"""Microsoft Outlook / Graph API calendar integration using httpx."""


import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.calendar import Event
from app.models.integration import OAuthCredential

logger = logging.getLogger(__name__)
settings = get_settings()

MICROSOFT_TOKEN_URL = (
    "https://login.microsoftonline.com/common/oauth2/v2.0/token"
)
GRAPH_BASE = "https://graph.microsoft.com/v1.0"

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # seconds


class OutlookCalendarClient:
    """Client for Microsoft Graph Calendar API."""

    def __init__(self, credential: OAuthCredential) -> None:
        self.credential = credential
        self._client = httpx.AsyncClient(
            base_url=GRAPH_BASE,
            timeout=30.0,
        )

    async def close(self) -> None:
        await self._client.aclose()

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.credential.access_token}"}

    # ── Token management ─────────────────────────────────────────────────

    async def refresh_token_if_needed(self, db: AsyncSession) -> None:
        """Refresh the access token if it has expired or is about to expire."""
        if self.credential.token_expiry is None:
            return

        now = datetime.now(timezone.utc)
        if self.credential.token_expiry.timestamp() - now.timestamp() > 60:
            return

        if not self.credential.refresh_token:
            logger.error(
                "No refresh token available for credential %s", self.credential.id
            )
            return

        payload = {
            "client_id": settings.MICROSOFT_CLIENT_ID,
            "client_secret": settings.MICROSOFT_CLIENT_SECRET,
            "refresh_token": self.credential.refresh_token,
            "grant_type": "refresh_token",
            "scope": "https://graph.microsoft.com/.default offline_access",
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(MICROSOFT_TOKEN_URL, data=payload)
            resp.raise_for_status()
            data = resp.json()

        self.credential.access_token = data["access_token"]
        if "refresh_token" in data:
            self.credential.refresh_token = data["refresh_token"]
        expires_in = data.get("expires_in", 3600)
        self.credential.token_expiry = datetime.fromtimestamp(
            now.timestamp() + expires_in, tz=timezone.utc
        )

        db.add(self.credential)
        await db.flush()
        logger.info("Refreshed Microsoft token for credential %s", self.credential.id)

    # ── API helpers ──────────────────────────────────────────────────────

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Execute an HTTP request with exponential backoff on retryable errors."""
        import asyncio

        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                resp = await self._client.request(
                    method, url, headers=self._auth_headers(), **kwargs
                )
                if resp.status_code == 429 or resp.status_code >= 500:
                    retry_after = int(
                        resp.headers.get("Retry-After", RETRY_BACKOFF_BASE ** attempt)
                    )
                    logger.warning(
                        "Graph API %s %s returned %s, retrying in %ss",
                        method, url, resp.status_code, retry_after,
                    )
                    await asyncio.sleep(retry_after)
                    continue
                resp.raise_for_status()
                return resp
            except httpx.HTTPStatusError:
                raise
            except httpx.HTTPError as exc:
                last_exc = exc
                wait = RETRY_BACKOFF_BASE ** attempt
                logger.warning("Graph API request error: %s, retrying in %ss", exc, wait)
                await asyncio.sleep(wait)

        raise last_exc or RuntimeError("Request failed after retries")

    # ── Calendar operations ──────────────────────────────────────────────

    async def list_calendars(self) -> list[dict]:
        """List all calendars for the authenticated user."""
        resp = await self._request_with_retry("GET", "/me/calendars")
        return resp.json().get("value", [])

    async def sync_events(
        self,
        calendar_id: str,
        delta_link: str | None = None,
    ) -> tuple[list[dict], str]:
        """Fetch events using delta queries for incremental sync.

        Returns (events, new_delta_link).
        """
        all_events: list[dict] = []

        if delta_link:
            # Resume from previous delta link (full URL)
            url = delta_link
            use_base = False
        else:
            url = f"/me/calendars/{calendar_id}/events/delta"
            use_base = True

        new_delta_link = ""

        while True:
            if use_base:
                resp = await self._request_with_retry("GET", url)
            else:
                # delta_link is an absolute URL
                resp = await self._request_with_retry("GET", url)

            data = resp.json()
            all_events.extend(data.get("value", []))

            next_link = data.get("@odata.nextLink")
            if next_link:
                url = next_link
                use_base = False
                continue

            new_delta_link = data.get("@odata.deltaLink", "")
            break

        return all_events, new_delta_link

    async def create_event(self, calendar_id: str, event_data: dict) -> dict:
        """Create an event in an Outlook calendar."""
        resp = await self._request_with_retry(
            "POST",
            f"/me/calendars/{calendar_id}/events",
            json=event_data,
        )
        return resp.json()

    async def update_event(
        self, calendar_id: str, event_id: str, event_data: dict
    ) -> dict:
        """Update (PATCH) an existing Outlook event."""
        resp = await self._request_with_retry(
            "PATCH",
            f"/me/events/{event_id}",
            json=event_data,
        )
        return resp.json()

    async def delete_event(self, calendar_id: str, event_id: str) -> None:
        """Delete an event from an Outlook calendar."""
        await self._request_with_retry("DELETE", f"/me/events/{event_id}")


# ── Mapping helpers ──────────────────────────────────────────────────────────


def map_outlook_event_to_local(outlook_event: dict) -> dict:
    """Map a Microsoft Graph event to local Event model fields."""
    start = outlook_event.get("start", {})
    end = outlook_event.get("end", {})

    all_day = outlook_event.get("isAllDay", False)

    start_tz = start.get("timeZone", "UTC")
    end_tz = end.get("timeZone", "UTC")

    start_dt = start.get("dateTime", "")
    end_dt = end.get("dateTime", "")

    # Graph returns ISO 8601 without offset when timeZone is provided
    if start_dt and not start_dt.endswith("Z") and "+" not in start_dt:
        start_time = datetime.fromisoformat(start_dt)
    else:
        start_time = datetime.fromisoformat(start_dt)

    if end_dt and not end_dt.endswith("Z") and "+" not in end_dt:
        end_time = datetime.fromisoformat(end_dt)
    else:
        end_time = datetime.fromisoformat(end_dt)

    # Recurrence
    recurrence = outlook_event.get("recurrence")
    recurrence_rule = None
    if recurrence and recurrence.get("pattern"):
        pattern = recurrence["pattern"]
        recurrence_rule = _outlook_recurrence_to_rrule(pattern)

    body = outlook_event.get("body", {})
    description = body.get("content") if body.get("contentType") == "text" else None

    return {
        "external_id": outlook_event.get("id"),
        "title": outlook_event.get("subject", "(No title)"),
        "description": description,
        "location": _extract_outlook_location(outlook_event),
        "start_time": start_time,
        "end_time": end_time,
        "all_day": all_day,
        "recurrence_rule": recurrence_rule,
        "is_private": outlook_event.get("sensitivity") == "private",
    }


def _extract_outlook_location(event: dict) -> str | None:
    """Extract a display location string from an Outlook event."""
    loc = event.get("location", {})
    if isinstance(loc, dict):
        return loc.get("displayName") or None
    return None


def _outlook_recurrence_to_rrule(pattern: dict) -> str:
    """Convert an Outlook recurrence pattern dict to an iCal RRULE string."""
    freq_map = {
        "daily": "DAILY",
        "weekly": "WEEKLY",
        "absoluteMonthly": "MONTHLY",
        "relativeMonthly": "MONTHLY",
        "absoluteYearly": "YEARLY",
        "relativeYearly": "YEARLY",
    }
    freq = freq_map.get(pattern.get("type", ""), "DAILY")
    interval = pattern.get("interval", 1)
    return f"RRULE:FREQ={freq};INTERVAL={interval}"


def map_local_event_to_outlook(event: Event) -> dict:
    """Map a local Event model instance to Microsoft Graph event format."""
    result: dict[str, Any] = {
        "subject": event.title,
        "isAllDay": event.all_day,
    }

    if event.description:
        result["body"] = {"contentType": "text", "content": event.description}
    if event.location:
        result["location"] = {"displayName": event.location}

    if event.all_day:
        result["start"] = {
            "dateTime": event.start_time.strftime("%Y-%m-%dT00:00:00"),
            "timeZone": "UTC",
        }
        result["end"] = {
            "dateTime": event.end_time.strftime("%Y-%m-%dT00:00:00"),
            "timeZone": "UTC",
        }
    else:
        result["start"] = {
            "dateTime": event.start_time.isoformat(),
            "timeZone": "UTC",
        }
        result["end"] = {
            "dateTime": event.end_time.isoformat(),
            "timeZone": "UTC",
        }

    if event.is_private:
        result["sensitivity"] = "private"

    return result
