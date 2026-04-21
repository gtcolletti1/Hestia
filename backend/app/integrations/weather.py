"""Open-Meteo weather integration using httpx (no API key required)."""


import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

OPEN_METEO_BASE = "https://api.open-meteo.com/v1"

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2

# Map WMO weather codes to OWM-style icon codes (day variants) and descriptions.
_WMO_MAP: dict[int, tuple[str, str]] = {
    0: ("01d", "clear sky"),
    1: ("02d", "mainly clear"),
    2: ("03d", "partly cloudy"),
    3: ("04d", "overcast"),
    45: ("50d", "fog"),
    48: ("50d", "depositing rime fog"),
    51: ("09d", "light drizzle"),
    53: ("09d", "moderate drizzle"),
    55: ("09d", "dense drizzle"),
    56: ("09d", "light freezing drizzle"),
    57: ("09d", "dense freezing drizzle"),
    61: ("10d", "slight rain"),
    63: ("10d", "moderate rain"),
    65: ("10d", "heavy rain"),
    66: ("10d", "light freezing rain"),
    67: ("10d", "heavy freezing rain"),
    71: ("13d", "slight snow"),
    73: ("13d", "moderate snow"),
    75: ("13d", "heavy snow"),
    77: ("13d", "snow grains"),
    80: ("09d", "slight rain showers"),
    81: ("09d", "moderate rain showers"),
    82: ("09d", "violent rain showers"),
    85: ("13d", "slight snow showers"),
    86: ("13d", "heavy snow showers"),
    95: ("11d", "thunderstorm"),
    96: ("11d", "thunderstorm with slight hail"),
    99: ("11d", "thunderstorm with heavy hail"),
}


class WeatherClient:
    """Client for the Open-Meteo API (free, no key required)."""

    def __init__(self, api_key: str = "") -> None:
        # api_key kept in signature for backward compatibility but is unused
        self._client = httpx.AsyncClient(base_url=OPEN_METEO_BASE, timeout=15.0)

    async def close(self) -> None:
        await self._client.aclose()

    async def _request_with_retry(
        self, url: str, params: dict[str, Any]
    ) -> dict:
        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                resp = await self._client.get(url, params=params)
                if resp.status_code == 429 or resp.status_code >= 500:
                    wait = RETRY_BACKOFF_BASE ** attempt
                    logger.warning(
                        "Open-Meteo %s returned %s, retrying in %ss",
                        url, resp.status_code, wait,
                    )
                    await asyncio.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError:
                raise
            except httpx.HTTPError as exc:
                last_exc = exc
                wait = RETRY_BACKOFF_BASE ** attempt
                logger.warning("Open-Meteo request error: %s, retrying in %ss", exc, wait)
                await asyncio.sleep(wait)

        raise last_exc or RuntimeError("Open-Meteo request failed after retries")

    async def get_forecast(self, lat: float, lon: float) -> dict:
        """Get current conditions + 3-day daily forecast.

        Returns the same simplified shape the frontend expects.
        """
        data = await self._request_with_retry("/forecast", {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min",
            "forecast_days": 4,
            "timezone": "auto",
        })
        return _simplify(data)


# ── Response simplification ──────────────────────────────────────────────────


def _wmo_to_icon_desc(code: int | None) -> tuple[str, str]:
    """Convert a WMO weather code to (icon, description)."""
    if code is None:
        return ("02d", "partly cloudy")
    return _WMO_MAP.get(code, ("02d", "partly cloudy"))


def _simplify(data: dict) -> dict:
    """Convert Open-Meteo response into the shape the frontend expects.

    All temps are returned in Celsius; the frontend handles unit conversion.
    """
    current = data.get("current", {})
    icon, desc = _wmo_to_icon_desc(current.get("weather_code"))

    daily = data.get("daily", {})
    dates = daily.get("time", [])
    highs = daily.get("temperature_2m_max", [])
    lows = daily.get("temperature_2m_min", [])
    codes = daily.get("weather_code", [])

    forecast = []
    for i, d in enumerate(dates):
        fc_icon, fc_desc = _wmo_to_icon_desc(codes[i] if i < len(codes) else None)
        forecast.append({
            "date": d,
            "high": highs[i] if i < len(highs) else 0,
            "low": lows[i] if i < len(lows) else 0,
            "description": fc_desc,
            "icon": fc_icon,
        })

    return {
        "temp": current.get("temperature_2m"),
        "feels_like": current.get("apparent_temperature"),
        "description": desc,
        "icon": icon,
        "humidity": current.get("relative_humidity_2m"),
        "wind_speed": current.get("wind_speed_10m"),
        "forecast": forecast[:3],
    }
