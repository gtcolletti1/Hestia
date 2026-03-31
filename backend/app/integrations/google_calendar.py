"""Google Calendar API integration using httpx."""

from __future__ import annotations

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

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CALENDAR_BASE = "https://www.googleapis.com/calendar/v3"

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # seconds


class GoogleCalendarClient:
    """Client for Google Calendar API v3."""

    def __init__(self, credential: OAuthCredential) -> None:
        self.credential = credential
        self._client = httpx.AsyncClient(
            base_url=GOOGLE_CALENDAR_BASE,
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
        # Refresh 60 seconds before actual expiry to avoid race conditions
        if self.credential.token_expiry.timestamp() - now.timestamp() > 60:
            return

        if not self.credential.refresh_token:
            logger.error("No refresh token available for credential %s", self.credential.id)
            return

        payload = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "refresh_token": self.credential.refresh_token,
            "grant_type": "refresh_token",
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(GOOGLE_TOKEN_URL, data=payload)
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
        logger.info("Refreshed Google token for credential %s", self.credential.id)

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
                    wait = RETRY_BACKOFF_BASE ** attempt
                    logger.warning(
                        "Google API %s %s returned %s, retrying in %ss",
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
                logger.warning("Google API request error: %s, retrying in %ss", exc, wait)
                await asyncio.sleep(wait)

        raise last_exc or RuntimeError("Request failed after retries")

    # ── Calendar operations ──────────────────────────────────────────────

    async def list_calendars(self) -> list[dict]:
        """List all calendars for the authenticated user."""
        resp = await self._request_with_retry("GET", "/users/me/calendarList")
        return resp.json().get("items", [])

    async def sync_events(
        self,
        calendar_id: str,
        sync_token: str | None = None,
    ) -> tuple[list[dict], str]:
        """Fetch events using incremental sync.

        Returns (events, new_sync_token).
        """
        all_events: list[dict] = []
        params: dict[str, Any] = {"maxResults": 250, "singleEvents": True}

        if sync_token:
            params["syncToken"] = sync_token
        else:
            # Full sync — only future events by default
            params["timeMin"] = datetime.now(timezone.utc).isoformat()

        page_token: str | None = None
        new_sync_token = ""

        while True:
            if page_token:
                params["pageToken"] = page_token

            try:
                resp = await self._request_with_retry(
                    "GET",
                    f"/calendars/{calendar_id}/events",
                    params=params,
                )
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 410:
                    # Sync token invalidated — do a full sync
                    logger.warning("Sync token expired for calendar %s, doing full sync", calendar_id)
                    return await self.sync_events(calendar_id, sync_token=None)
                raise

            data = resp.json()
            all_events.extend(data.get("items", []))

            page_token = data.get("nextPageToken")
            if not page_token:
                new_sync_token = data.get("nextSyncToken", "")
                break

        return all_events, new_sync_token

    async def create_event(self, calendar_id: str, event_data: dict) -> dict:
        """Create an event on a Google Calendar."""
        resp = await self._request_with_retry(
            "POST",
            f"/calendars/{calendar_id}/events",
            json=event_data,
        )
        return resp.json()

    async def update_event(
        self, calendar_id: str, event_id: str, event_data: dict
    ) -> dict:
        """Update (PATCH) an existing event."""
        resp = await self._request_with_retry(
            "PATCH",
            f"/calendars/{calendar_id}/events/{event_id}",
            json=event_data,
        )
        return resp.json()

    async def delete_event(self, calendar_id: str, event_id: str) -> None:
        """Delete an event from a Google Calendar."""
        await self._request_with_retry(
            "DELETE",
            f"/calendars/{calendar_id}/events/{event_id}",
        )


# ── Mapping helpers ──────────────────────────────────────────────────────────


def map_google_event_to_local(google_event: dict) -> dict:
    """Map a Google Calendar event to local Event model fields."""
    start = google_event.get("start", {})
    end = google_event.get("end", {})

    # All-day events use "date"; timed events use "dateTime"
    all_day = "date" in start and "dateTime" not in start

    if all_day:
        start_time = datetime.fromisoformat(start["date"])
        # Google all-day end dates are exclusive; keep as-is for storage
        end_time = datetime.fromisoformat(end.get("date", start["date"]))
    else:
        start_time = datetime.fromisoformat(start.get("dateTime", ""))
        end_time = datetime.fromisoformat(end.get("dateTime", ""))

    recurrence = google_event.get("recurrence")
    recurrence_rule = recurrence[0] if recurrence else None

    return {
        "external_id": google_event.get("id"),
        "title": google_event.get("summary", "(No title)"),
        "description": google_event.get("description"),
        "location": google_event.get("location"),
        "start_time": start_time,
        "end_time": end_time,
        "all_day": all_day,
        "recurrence_rule": recurrence_rule,
        "is_private": google_event.get("visibility") == "private",
    }


def map_local_event_to_google(event: Event) -> dict:
    """Map a local Event model instance to Google Calendar API format."""
    result: dict[str, Any] = {
        "summary": event.title,
    }

    if event.description:
        result["description"] = event.description
    if event.location:
        result["location"] = event.location

    if event.all_day:
        result["start"] = {"date": event.start_time.strftime("%Y-%m-%d")}
        result["end"] = {"date": event.end_time.strftime("%Y-%m-%d")}
    else:
        tz = event.start_time.tzname() or "UTC"
        result["start"] = {
            "dateTime": event.start_time.isoformat(),
            "timeZone": tz,
        }
        result["end"] = {
            "dateTime": event.end_time.isoformat(),
            "timeZone": tz,
        }

    if event.recurrence_rule:
        result["recurrence"] = [event.recurrence_rule]

    if event.is_private:
        result["visibility"] = "private"

    return result
