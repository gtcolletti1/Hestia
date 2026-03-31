"""Home Assistant integration helpers."""

import logging
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Household

logger = logging.getLogger(__name__)


async def get_status(db: AsyncSession, household_id: uuid.UUID) -> dict:
    """Return the current Home Assistant integration status for a household.

    Reads the HA webhook URL from household settings and returns a summary
    of the current state (active routines, next event, connectivity).
    """
    result = await db.execute(select(Household).where(Household.id == household_id))
    household = result.scalar_one_or_none()
    if household is None:
        return {"connected": False, "error": "Household not found"}

    ha_settings = (household.settings or {}).get("homeassistant", {})
    webhook_url = ha_settings.get("webhook_url")

    if not webhook_url:
        return {"connected": False, "error": "Home Assistant webhook URL not configured"}

    return {
        "connected": True,
        "webhook_url": webhook_url,
        "active_routines": ha_settings.get("active_routines", []),
        "next_event": ha_settings.get("next_event"),
    }


async def send_webhook(url: str, event_type: str, data: dict) -> dict:
    """POST a webhook payload to Home Assistant.

    Returns the response body or raises on failure.
    """
    payload = {"type": event_type, "data": data}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        logger.info("Sent HA webhook (%s) to %s", event_type, url)
        try:
            return resp.json()
        except Exception:
            return {"status": "ok"}


async def notify_routine_complete(
    db: AsyncSession,
    household_id: uuid.UUID,
    routine_id: uuid.UUID,
) -> None:
    """Send a webhook to HA when a routine is marked as completed."""
    status_info = await get_status(db, household_id)
    webhook_url = status_info.get("webhook_url")

    if not webhook_url:
        logger.warning(
            "Cannot notify HA for household %s — no webhook URL configured",
            household_id,
        )
        return

    await send_webhook(
        url=webhook_url,
        event_type="routine_complete",
        data={
            "household_id": str(household_id),
            "routine_id": str(routine_id),
        },
    )
