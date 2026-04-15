"""API route for weather data."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_profile
from app.config import get_settings
from app.database import get_db
from app.integrations.weather import WeatherClient
from app.models.user import Household, Profile

router = APIRouter(tags=["weather"])
settings = get_settings()


@router.get("/weather")
async def get_weather(
    household_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> dict:
    """Return current weather and 3-day forecast for the household location."""
    if current_profile.household_id != household_id:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(
        select(Household).where(Household.id == household_id)
    )
    household = result.scalar_one_or_none()
    if household is None:
        raise HTTPException(status_code=404, detail="Household not found")

    stored = household.settings or {}
    lat = stored.get("weather_lat")
    lon = stored.get("weather_lon")
    units = stored.get("weather_units", "imperial")

    if not lat or not lon:
        raise HTTPException(
            status_code=422,
            detail="Weather location not configured. Set latitude/longitude in Settings.",
        )

    api_key = settings.OPENWEATHERMAP_API_KEY
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Weather service not configured (missing API key).",
        )

    client = WeatherClient(api_key)
    try:
        data = await client.get_forecast(float(lat), float(lon))
        # Trim forecast to 3 days
        data["forecast"] = data.get("forecast", [])[:3]
        data["units"] = units
        return data
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Weather service error: {exc}"
        )
    finally:
        await client.close()
