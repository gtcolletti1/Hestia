"""Pydantic v2 schemas for Admin / Household settings."""


from pydantic import BaseModel


class ModulesEnabled(BaseModel):
    calendar: bool = True
    routines: bool = True
    lists: bool = True
    meals: bool = True


class HouseholdSettings(BaseModel):
    name: str
    theme: str = "light"  # "light" | "dark"
    accent_color: str = "#4F46E5"
    modules_enabled: ModulesEnabled = ModulesEnabled()
    privacy_mode: bool = False


class HouseholdSettingsUpdate(BaseModel):
    name: str | None = None
    theme: str | None = None
    accent_color: str | None = None
    modules_enabled: ModulesEnabled | None = None
    privacy_mode: bool | None = None


class ModuleToggle(BaseModel):
    module: str
    enabled: bool
