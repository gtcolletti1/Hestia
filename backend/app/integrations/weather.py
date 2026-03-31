"""OpenWeatherMap weather integration using httpx."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

OWM_BASE = "https://api.openweathermap.org/data/2.5"

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2


class WeatherClient:
    """Client for the OpenWeatherMap API."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._client = httpx.AsyncClient(base_url=OWM_BASE, timeout=15.0)

    async def close(self) -> None:
        await self._client.aclose()

    async def _request_with_retry(
        self, url: str, params: dict[str, Any]
    ) -> dict:
        import asyncio

        params["appid"] = self.api_key
        params["units"] = "metric"

        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                resp = await self._client.get(url, params=params)
                if resp.status_code == 429 or resp.status_code >= 500:
                    wait = RETRY_BACKOFF_BASE ** attempt
                    logger.warning(
                        "OWM %s returned %s, retrying in %ss",
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
                logger.warning("OWM request error: %s, retrying in %ss", exc, wait)
                await asyncio.sleep(wait)

        raise last_exc or RuntimeError("OWM request failed after retries")

    async def get_current(self, lat: float, lon: float) -> dict:
        """Get current weather for a location.

        Returns a simplified dict with key weather data.
        """
        data = await self._request_with_retry(
            "/weather", {"lat": lat, "lon": lon}
        )
        return _simplify_current(data)

    async def get_forecast(self, lat: float, lon: float) -> dict:
        """Get a 5-day / 3-hour forecast for a location.

        Returns current conditions plus a daily summary forecast list.
        """
        data = await self._request_with_retry(
            "/forecast", {"lat": lat, "lon": lon}
        )
        return _simplify_forecast(data)


# ── Response simplification ──────────────────────────────────────────────────


def _simplify_current(data: dict) -> dict:
    """Simplify raw OWM current-weather response."""
    main = data.get("main", {})
    weather = data.get("weather", [{}])[0]
    wind = data.get("wind", {})

    return {
        "temp": main.get("temp"),
        "feels_like": main.get("feels_like"),
        "description": weather.get("description"),
        "icon": weather.get("icon"),
        "humidity": main.get("humidity"),
        "wind_speed": wind.get("speed"),
    }


def _simplify_forecast(data: dict) -> dict:
    """Simplify raw OWM 5-day forecast into daily summaries."""
    daily: dict[str, dict] = {}

    for entry in data.get("list", []):
        dt_txt = entry.get("dt_txt", "")
        date_str = dt_txt[:10]  # YYYY-MM-DD
        if not date_str:
            continue

        main = entry.get("main", {})
        weather = entry.get("weather", [{}])[0]
        temp = main.get("temp", 0)

        if date_str not in daily:
            daily[date_str] = {
                "date": date_str,
                "high": temp,
                "low": temp,
                "description": weather.get("description"),
                "icon": weather.get("icon"),
            }
        else:
            day = daily[date_str]
            day["high"] = max(day["high"], temp)
            day["low"] = min(day["low"], temp)

    # Also include simplified current from the first entry
    first = data.get("list", [{}])[0] if data.get("list") else {}
    first_main = first.get("main", {})
    first_weather = first.get("weather", [{}])[0]
    first_wind = first.get("wind", {})

    return {
        "temp": first_main.get("temp"),
        "feels_like": first_main.get("feels_like"),
        "description": first_weather.get("description"),
        "icon": first_weather.get("icon"),
        "humidity": first_main.get("humidity"),
        "wind_speed": first_wind.get("speed"),
        "forecast": sorted(daily.values(), key=lambda d: d["date"]),
    }
