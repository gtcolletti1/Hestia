"""Pydantic v2 schemas for Admin / Household settings."""


from typing import Literal

from pydantic import BaseModel, Field


SplashMode = Literal["ambient", "photo", "alternating"]
SplashCalendarMode = Literal["off", "busy_only", "hidden"]


class ModulesEnabled(BaseModel):
    calendar: bool = True
    routines: bool = True
    lists: bool = True
    meals: bool = True
    weather: bool = True
    screensaver: bool = True
    messages: bool = True
    notifications: bool = True
    rewards: bool = True


class HouseholdSettings(BaseModel):
    name: str
    theme: str = "light"  # "light" | "dark"
    accent_color: str = "#4F46E5"
    modules_enabled: ModulesEnabled = ModulesEnabled()
    time_format: Literal["12h", "24h"] = "12h"
    timezone: str = "UTC"  # IANA name, e.g. "America/New_York"
    weather_lat: float | None = None
    weather_lon: float | None = None
    weather_units: str = "imperial"  # "imperial" | "metric"
    screensaver_timeout_minutes: int = 2
    screensaver_transition_seconds: int = 10

    # Splash & Pre-Login Privacy (PRD §2.12, v2.2). Replaces the legacy
    # post-login `privacy_mode` boolean, which was migrated server-side.
    splash_mode: SplashMode = "ambient"
    splash_alternating_ambient_seconds: int = Field(default=60, ge=10, le=600)
    splash_alternating_photo_seconds: int = Field(default=60, ge=10, le=600)
    splash_agenda_max_days: int = Field(default=3, ge=1, le=7)
    splash_calendar_mode: SplashCalendarMode = "off"
    splash_show_routines: bool = True
    splash_show_meals: bool = False
    splash_show_weather: bool = True
    splash_show_messages: bool = False


class HouseholdSettingsUpdate(BaseModel):
    name: str | None = None
    theme: str | None = None
    accent_color: str | None = None
    modules_enabled: ModulesEnabled | None = None
    time_format: Literal["12h", "24h"] | None = None
    timezone: str | None = None
    weather_lat: float | None = None
    weather_lon: float | None = None
    weather_units: str | None = None
    screensaver_timeout_minutes: int | None = None
    screensaver_transition_seconds: int | None = None

    splash_mode: SplashMode | None = None
    splash_alternating_ambient_seconds: int | None = Field(default=None, ge=10, le=600)
    splash_alternating_photo_seconds: int | None = Field(default=None, ge=10, le=600)
    splash_agenda_max_days: int | None = Field(default=None, ge=1, le=7)
    splash_calendar_mode: SplashCalendarMode | None = None
    splash_show_routines: bool | None = None
    splash_show_meals: bool | None = None
    splash_show_weather: bool | None = None
    splash_show_messages: bool | None = None


class ModuleToggle(BaseModel):
    module: str
    enabled: bool
