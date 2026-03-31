"""API routes for integration management (OAuth flows, sync triggers, status)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.integration import OAuthCredential, OAuthProvider
from app.models.calendar import SourceCalendar, CalendarProvider
from app.tasks.calendar_sync import sync_all_calendars_task, sync_single_calendar_task

import httpx

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(tags=["integrations"])


# ── Google OAuth ─────────────────────────────────────────────────────────────

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_SCOPES = "https://www.googleapis.com/auth/calendar"


@router.get("/integrations/oauth/google/authorize")
async def google_authorize(
    household_id: uuid.UUID = Query(...),
) -> dict:
    """Return Google OAuth authorization URL."""
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": GOOGLE_SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "state": str(household_id),
    }
    url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return {"authorization_url": url}


@router.get("/integrations/oauth/google/callback")
async def google_callback(
    code: str = Query(...),
    state: str = Query(""),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Handle Google OAuth callback: exchange code for tokens and store."""
    payload = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(GOOGLE_TOKEN_URL, data=payload)
        if resp.status_code != 200:
            logger.error("Google token exchange failed: %s", resp.text)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to exchange authorization code",
            )
        data = resp.json()

    household_id = uuid.UUID(state) if state else None
    if not household_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing household_id in state parameter",
        )

    now = datetime.now(timezone.utc)
    expires_in = data.get("expires_in", 3600)

    # Upsert credential
    stmt = select(OAuthCredential).where(
        OAuthCredential.household_id == household_id,
        OAuthCredential.provider == OAuthProvider.google,
    )
    result = await db.execute(stmt)
    credential = result.scalars().first()

    if credential:
        credential.access_token = data["access_token"]
        credential.refresh_token = data.get("refresh_token", credential.refresh_token)
        credential.token_expiry = datetime.fromtimestamp(
            now.timestamp() + expires_in, tz=timezone.utc
        )
        credential.scopes = GOOGLE_SCOPES
    else:
        credential = OAuthCredential(
            household_id=household_id,
            provider=OAuthProvider.google,
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            token_expiry=datetime.fromtimestamp(
                now.timestamp() + expires_in, tz=timezone.utc
            ),
            scopes=GOOGLE_SCOPES,
        )
        db.add(credential)

    await db.flush()
    return {"status": "connected", "provider": "google"}


# ── Microsoft OAuth ──────────────────────────────────────────────────────────

MICROSOFT_AUTH_URL = (
    "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
)
MICROSOFT_TOKEN_URL = (
    "https://login.microsoftonline.com/common/oauth2/v2.0/token"
)
MICROSOFT_SCOPES = "Calendars.ReadWrite offline_access"


@router.get("/integrations/oauth/microsoft/authorize")
async def microsoft_authorize(
    household_id: uuid.UUID = Query(...),
) -> dict:
    """Return Microsoft OAuth authorization URL."""
    params = {
        "client_id": settings.MICROSOFT_CLIENT_ID,
        "redirect_uri": settings.MICROSOFT_REDIRECT_URI,
        "response_type": "code",
        "scope": MICROSOFT_SCOPES,
        "state": str(household_id),
    }
    url = f"{MICROSOFT_AUTH_URL}?{urlencode(params)}"
    return {"authorization_url": url}


@router.get("/integrations/oauth/microsoft/callback")
async def microsoft_callback(
    code: str = Query(...),
    state: str = Query(""),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Handle Microsoft OAuth callback: exchange code for tokens and store."""
    payload = {
        "client_id": settings.MICROSOFT_CLIENT_ID,
        "client_secret": settings.MICROSOFT_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": settings.MICROSOFT_REDIRECT_URI,
        "scope": MICROSOFT_SCOPES,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(MICROSOFT_TOKEN_URL, data=payload)
        if resp.status_code != 200:
            logger.error("Microsoft token exchange failed: %s", resp.text)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to exchange authorization code",
            )
        data = resp.json()

    household_id = uuid.UUID(state) if state else None
    if not household_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing household_id in state parameter",
        )

    now = datetime.now(timezone.utc)
    expires_in = data.get("expires_in", 3600)

    stmt = select(OAuthCredential).where(
        OAuthCredential.household_id == household_id,
        OAuthCredential.provider == OAuthProvider.microsoft,
    )
    result = await db.execute(stmt)
    credential = result.scalars().first()

    if credential:
        credential.access_token = data["access_token"]
        credential.refresh_token = data.get("refresh_token", credential.refresh_token)
        credential.token_expiry = datetime.fromtimestamp(
            now.timestamp() + expires_in, tz=timezone.utc
        )
        credential.scopes = MICROSOFT_SCOPES
    else:
        credential = OAuthCredential(
            household_id=household_id,
            provider=OAuthProvider.microsoft,
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            token_expiry=datetime.fromtimestamp(
                now.timestamp() + expires_in, tz=timezone.utc
            ),
            scopes=MICROSOFT_SCOPES,
        )
        db.add(credential)

    await db.flush()
    return {"status": "connected", "provider": "microsoft"}


# ── Sync triggers ────────────────────────────────────────────────────────────


@router.get("/integrations/calendars/sync/{source_calendar_id}")
async def trigger_sync(
    source_calendar_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Trigger a manual sync for a single source calendar."""
    cal = await db.get(SourceCalendar, source_calendar_id)
    if not cal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source calendar not found",
        )

    sync_single_calendar_task.delay(str(source_calendar_id))
    return {"status": "sync_queued", "calendar_id": str(source_calendar_id)}


@router.get("/integrations/calendars/sync-all")
async def trigger_sync_all(
    household_id: uuid.UUID = Query(...),
) -> dict:
    """Trigger sync for all external calendars in a household."""
    sync_all_calendars_task.delay(str(household_id))
    return {"status": "sync_queued", "household_id": str(household_id)}


# ── Integration status ───────────────────────────────────────────────────────


@router.get("/integrations/status")
async def integration_status(
    household_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get integration status showing which providers are connected."""
    stmt = select(OAuthCredential).where(
        OAuthCredential.household_id == household_id
    )
    result = await db.execute(stmt)
    credentials = list(result.scalars().all())

    providers: dict[str, dict] = {}
    for cred in credentials:
        providers[cred.provider.value] = {
            "connected": True,
            "account_email": cred.account_email,
            "token_expiry": cred.token_expiry.isoformat() if cred.token_expiry else None,
        }

    # Include calendar counts per provider
    cal_stmt = select(SourceCalendar).where(
        SourceCalendar.household_id == household_id,
        SourceCalendar.provider != CalendarProvider.local,
    )
    cal_result = await db.execute(cal_stmt)
    calendars = list(cal_result.scalars().all())

    calendar_summary: list[dict] = [
        {
            "id": str(c.id),
            "name": c.name,
            "provider": c.provider.value,
            "last_synced_at": c.last_synced_at.isoformat() if c.last_synced_at else None,
        }
        for c in calendars
    ]

    return {
        "household_id": str(household_id),
        "providers": providers,
        "calendars": calendar_summary,
    }
