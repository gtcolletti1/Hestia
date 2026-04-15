"""Pydantic v2 schemas for Admin / Household settings."""


from pydantic import BaseModel


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
    privacy_mode: bool = False
    weather_lat: float | None = None
    weather_lon: float | None = None
    weather_units: str = "imperial"  # "imperial" | "metric"
    screensaver_timeout_minutes: int = 2
    screensaver_transition_seconds: int = 10


class HouseholdSettingsUpdate(BaseModel):
    name: str | None = None
    theme: str | None = None
    accent_color: str | None = None
    modules_enabled: ModulesEnabled | None = None
    privacy_mode: bool | None = None
    weather_lat: float | None = None
    weather_lon: float | None = None
    weather_units: str | None = None
    screensaver_timeout_minutes: int | None = None
    screensaver_transition_seconds: int | None = None


class ModuleToggle(BaseModel):
    module: str
    enabled: bool
