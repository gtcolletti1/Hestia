import { useState, useEffect, useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { admin, integrations as integrationsApi, photos as photosApi } from "@/api/endpoints";
import { useHouseholdStore } from "@/stores/householdStore";
import { useAuthStore } from "@/stores/authStore";
import { useThemeStore } from "@/stores/themeStore";
import SplashSettingsSection from "./SplashSettingsSection";
import type { SplashCalendarMode, SplashMode } from "@/types/splash";

type Theme = "light" | "dark";

interface HouseholdSettings {
  name: string;
  theme: Theme;
  accent_color: string;
  modules_enabled: {
    calendar: boolean;
    routines: boolean;
    lists: boolean;
    meals: boolean;
    weather: boolean;
  };
  time_format: "12h" | "24h";
  timezone: string;
  weather_lat: number | null;
  weather_lon: number | null;
  weather_units: string;
  screensaver_timeout_minutes: number;
  screensaver_transition_seconds: number;
  // Pre-login splash + privacy policy (PRD §2.12 / Hestia v2.2).
  splash_mode: SplashMode;
  splash_alternating_ambient_seconds: number;
  splash_alternating_photo_seconds: number;
  splash_calendar_mode: SplashCalendarMode;
  splash_agenda_max_days: number;
  splash_show_routines: boolean;
  splash_show_meals: boolean;
  splash_show_weather: boolean;
  splash_show_messages: boolean;
}

interface IcalCalendarSummary {
  id: string;
  name: string;
  provider: string;
  last_synced_at: string | null;
}

interface IntegrationStatus {
  google: boolean;
  microsoft: boolean;
  calendars?: IcalCalendarSummary[];
}

const DEFAULT_SETTINGS: HouseholdSettings = {
  name: "My Family",
  theme: useThemeStore.getState().theme,
  accent_color: useThemeStore.getState().accentColor,
  modules_enabled: {
    calendar: true,
    routines: true,
    lists: true,
    meals: true,
    weather: true,
  },
  time_format: "12h",
  timezone:
    (typeof Intl !== "undefined" && Intl.DateTimeFormat().resolvedOptions().timeZone) ||
    "UTC",
  weather_lat: null,
  weather_lon: null,
  weather_units: "imperial",
  screensaver_timeout_minutes: 2,
  screensaver_transition_seconds: 10,
  splash_mode: "ambient",
  splash_alternating_ambient_seconds: 60,
  splash_alternating_photo_seconds: 60,
  splash_calendar_mode: "off",
  splash_agenda_max_days: 3,
  splash_show_routines: true,
  splash_show_meals: false,
  splash_show_weather: true,
  splash_show_messages: false,
};

const ACCENT_COLORS = [
  "#3B82F6",
  "#EF4444",
  "#F97316",
  "#EAB308",
  "#22C55E",
  "#8B5CF6",
  "#EC4899",
  "#06B6D4",
];

export default function SettingsPanel() {
  const navigate = useNavigate();
  const householdId = useHouseholdStore((s) => s.householdId);
  const setHouseholdName = useHouseholdStore((s) => s.setHouseholdName);
  const currentProfile = useAuthStore((s) => s.profile);
  const isAdmin = currentProfile?.role === "admin";
  const queryClient = useQueryClient();
  const { data: settings } = useQuery({
    queryKey: ["settings", householdId],
    queryFn: () =>
      admin
        .getSettings(householdId!)
        .then((r) => r.data as HouseholdSettings)
        .catch(() => DEFAULT_SETTINGS),
    enabled: !!householdId,
    initialData: DEFAULT_SETTINGS,
  });

  const { data: integrationStatus } = useQuery({
    queryKey: ["integrations", "status", householdId],
    queryFn: () =>
      integrationsApi
        .getStatus(householdId!)
        .then((r) => r.data as IntegrationStatus)
        .catch<IntegrationStatus>(() => ({ google: false, microsoft: false, calendars: [] })),
    enabled: !!householdId,
  });

  const [form, setForm] = useState<HouseholdSettings>(settings);
  const [showSaved, setShowSaved] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    setForm(settings);
  }, [settings]);

  const saveMutation = useMutation({
    mutationFn: (data: HouseholdSettings) =>
      admin.updateSettings(householdId!, data as unknown as Record<string, unknown>),
    onSuccess: (_resp, submittedData) => {
      setSaveError(null);
      queryClient.invalidateQueries({ queryKey: ["settings"] });
      setHouseholdName(submittedData.name);
      setShowSaved(true);
      setTimeout(() => setShowSaved(false), 2500);
    },
    onError: (err: any) => {
      const status = err?.response?.status;
      if (status === 403) {
        setSaveError("Only admin profiles can change settings. Log in as an admin to make changes.");
      } else {
        setSaveError("Failed to save settings. Please try again.");
      }
      setTimeout(() => setSaveError(null), 5000);
    },
  });

  const moduleMutation = useMutation({
    mutationFn: (data: { module: string; enabled: boolean }) =>
      admin.toggleModule(householdId!, data),
    onSuccess: () => {
      setSaveError(null);
      queryClient.invalidateQueries({ queryKey: ["settings"] });
    },
    onError: (err: any) => {
      const status = err?.response?.status;
      if (status === 403) {
        setSaveError("Only admin profiles can toggle modules.");
      } else {
        setSaveError("Failed to update module. Please try again.");
      }
      setTimeout(() => setSaveError(null), 5000);
      // Revert the optimistic UI update
      queryClient.invalidateQueries({ queryKey: ["settings"] });
    },
  });

  const handleSave = useCallback(() => {
    saveMutation.mutate(form);
  }, [form, saveMutation]);

  const updateModules = (
    key: keyof HouseholdSettings["modules_enabled"],
    value: boolean,
  ) => {
    setForm((prev) => ({
      ...prev,
      modules_enabled: { ...prev.modules_enabled, [key]: value },
    }));
    if (isAdmin) {
      moduleMutation.mutate({ module: key, enabled: value });
    } else {
      setSaveError("Only admin profiles can toggle modules.");
      setTimeout(() => setSaveError(null), 5000);
    }
  };

  const handleThemeChange = (theme: Theme) => {
    const updated = { ...form, theme };
    setForm(updated);
    useThemeStore.getState().setTheme(theme);
    if (isAdmin) saveMutation.mutate(updated);
  };

  const handleAccentColor = (color: string) => {
    const updated = { ...form, accent_color: color };
    setForm(updated);
    useThemeStore.getState().setAccentColor(color);
    if (isAdmin) saveMutation.mutate(updated);
  };

  const connectGoogle = async () => {
    if (!householdId) return;
    try {
      const { data } = await integrationsApi.getGoogleAuthUrl(householdId);
      window.location.href = data.url;
    } catch {
      // handle error silently
    }
  };

  const connectMicrosoft = async () => {
    if (!householdId) return;
    try {
      const { data } = await integrationsApi.getMicrosoftAuthUrl(householdId);
      window.location.href = data.url;
    } catch {
      // handle error silently
    }
  };

  type IcalFormState = {
    open: boolean;
    name: string;
    url: string;
    error: string | null;
    errorKind: "duplicate" | "generic" | null;
    submitting: boolean;
  };
  const [icalForm, setIcalForm] = useState<IcalFormState>({
    open: false,
    name: "",
    url: "",
    error: null,
    errorKind: null,
    submitting: false,
  });

  const submitIcal = async () => {
    if (!householdId) return;
    setIcalForm((f) => ({ ...f, error: null, errorKind: null, submitting: true }));
    try {
      const { data } = await integrationsApi.subscribeIcal({
        household_id: householdId,
        name: icalForm.name.trim(),
        ical_url: icalForm.url.trim(),
      });
      setIcalForm({
        open: false,
        name: "",
        url: "",
        error: null,
        errorKind: null,
        submitting: false,
      });
      queryClient.invalidateQueries({ queryKey: ["integrations", "status"] });
      queryClient.invalidateQueries({ queryKey: ["events"] });
      // Toast: confirm preview event count
      setSaveError(null);
      setShowSaved(true);
      setTimeout(() => setShowSaved(false), 4000);
      console.info(`Subscribed: ${data.events_preview_count} events found`);
    } catch (err: unknown) {
      const response = (err as { response?: { status?: number; data?: { detail?: string } } })
        ?.response;
      const status = response?.status;
      const detail = response?.data?.detail;
      let message: string;
      let kind: "duplicate" | "generic";
      if (status === 409) {
        message =
          typeof detail === "string" && detail.length > 0
            ? detail
            : "This calendar is already connected to this household.";
        kind = "duplicate";
      } else {
        message =
          typeof detail === "string" && detail.length > 0
            ? detail
            : "Could not subscribe to that URL";
        kind = "generic";
      }
      setIcalForm((f) => ({
        ...f,
        error: message,
        errorKind: kind,
        submitting: false,
      }));
    }
  };

  const unsubscribeIcal = async (calendarId: string) => {
    if (!confirm("Remove this calendar subscription? Synced events will be deleted.")) return;
    try {
      await integrationsApi.unsubscribeIcal(calendarId);
      queryClient.invalidateQueries({ queryKey: ["integrations", "status"] });
      queryClient.invalidateQueries({ queryKey: ["events"] });
    } catch {
      // ignore
    }
  };

  const syncIcal = async (calendarId: string) => {
    try {
      await integrationsApi.syncCalendar(calendarId);
      setShowSaved(true);
      setTimeout(() => setShowSaved(false), 3000);
      // Re-fetch after a short delay so the sync has time to write events
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ["integrations", "status"] });
        queryClient.invalidateQueries({ queryKey: ["events"] });
      }, 2500);
    } catch {
      // ignore
    }
  };

  const icalCalendars = (integrationStatus?.calendars ?? []).filter(
    (c) => c.provider === "ical",
  );

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      {/* Header with back button */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => navigate("/")}
          className="flex items-center justify-center rounded-lg p-2 -ml-2 text-gray-500 hover:bg-gray-100 active:bg-gray-200 dark:text-gray-400 dark:hover:bg-gray-700 dark:active:bg-gray-600 transition-colors min-h-[44px] min-w-[44px]"
          aria-label="Back to dashboard"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Settings
        </h2>
      </div>

      {/* Admin-only banner */}
      {!isAdmin && (
        <div className="rounded-xl bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-800 p-4">
          <p className="text-sm font-medium text-amber-800 dark:text-amber-200">
            🔒 Admin access required to change settings.
          </p>
          <p className="text-xs text-amber-600 dark:text-amber-400 mt-1">
            You're logged in as <strong>{currentProfile?.name ?? "unknown"}</strong> ({currentProfile?.role}).
            Log in as an admin profile to make changes.
          </p>
        </div>
      )}

      {/* Error banner */}
      {saveError && (
        <div className="rounded-xl bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 p-4">
          <p className="text-sm text-red-700 dark:text-red-300">{saveError}</p>
        </div>
      )}

      {/* Household */}
      <section className="rounded-2xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          🏠 Household
        </h3>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Household Name
          </label>
          <input
            type="text"
            value={form.name}
            onChange={(e) =>
              setForm((prev) => ({
                ...prev,
                name: e.target.value,
              }))
            }
            className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-3 text-base text-gray-900 dark:text-gray-100 min-h-[44px]"
          />
        </div>
      </section>

      {/* Theme */}
      <section className="rounded-2xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          🎨 Theme
        </h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Dark Mode
            </span>
            <button
              type="button"
              onClick={() =>
                handleThemeChange(form.theme === "dark" ? "light" : "dark")
              }
              className={`relative inline-flex h-7 w-12 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors min-h-[44px] items-center ${
                form.theme === "dark"
                  ? "bg-blue-600"
                  : "bg-gray-300 dark:bg-gray-600"
              }`}
              role="switch"
              aria-checked={form.theme === "dark"}
            >
              <span
                className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${
                  form.theme === "dark"
                    ? "translate-x-5"
                    : "translate-x-0.5"
                }`}
              />
            </button>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Accent Color
            </label>
            <div className="flex flex-wrap gap-2">
              {ACCENT_COLORS.map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => handleAccentColor(c)}
                  className={`h-10 w-10 rounded-full min-h-[44px] min-w-[44px] transition-transform ${
                    form.accent_color === c
                      ? "ring-2 ring-offset-2 ring-blue-500 scale-110"
                      : "hover:scale-105"
                  }`}
                  style={{ backgroundColor: c }}
                  aria-label={`Accent color ${c}`}
                />
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Modules */}
      <section className="rounded-2xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          📦 Modules
        </h3>
        <div className="space-y-3">
          {(
            Object.entries(form.modules_enabled) as [
              keyof HouseholdSettings["modules_enabled"],
              boolean,
            ][]
          ).map(([key, enabled]) => (
            <div key={key} className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300 capitalize">
                {key}
              </span>
              <button
                type="button"
                onClick={() => updateModules(key, !enabled)}
                className={`relative inline-flex h-7 w-12 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors min-h-[44px] items-center ${
                  enabled ? "bg-blue-600" : "bg-gray-300 dark:bg-gray-600"
                }`}
                role="switch"
                aria-checked={enabled}
              >
                <span
                  className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${
                    enabled ? "translate-x-5" : "translate-x-0.5"
                  }`}
                />
              </button>
            </div>
          ))}
        </div>
      </section>

      {/* Pre-login splash + privacy policy (PRD §2.12). */}
      <SplashSettingsSection
        values={{
          splash_mode: form.splash_mode,
          splash_alternating_ambient_seconds: form.splash_alternating_ambient_seconds,
          splash_alternating_photo_seconds: form.splash_alternating_photo_seconds,
          splash_calendar_mode: form.splash_calendar_mode,
          splash_agenda_max_days: form.splash_agenda_max_days,
          splash_show_routines: form.splash_show_routines,
          splash_show_meals: form.splash_show_meals,
          splash_show_weather: form.splash_show_weather,
          splash_show_messages: form.splash_show_messages,
        }}
        onChange={(patch) => {
          const next = { ...form, ...patch };
          setForm(next);
          if (isAdmin) saveMutation.mutate(next);
        }}
        disabled={!isAdmin}
      />

      {/* Time Format */}
      <section className="rounded-2xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          🕐 Time Format
        </h3>
        <div className="flex items-center justify-between">
          <div>
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              24-Hour Clock
            </span>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Show {form.time_format === "24h" ? "14:30" : "2:30 PM"} format everywhere
            </p>
          </div>
          <button
            type="button"
            onClick={() => {
              const newFormat = form.time_format === "24h" ? "12h" : "24h";
              const updated = { ...form, time_format: newFormat as "12h" | "24h" };
              setForm(updated);
              if (isAdmin) saveMutation.mutate(updated);
            }}
            className={`relative inline-flex h-7 w-12 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors min-h-[44px] items-center ${
              form.time_format === "24h"
                ? "bg-blue-600"
                : "bg-gray-300 dark:bg-gray-600"
            }`}
            role="switch"
            aria-checked={form.time_format === "24h"}
          >
            <span
              className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${
                form.time_format === "24h" ? "translate-x-5" : "translate-x-0.5"
              }`}
            />
          </button>
        </div>

        {/* Timezone */}
        <div className="mt-6 border-t border-gray-200 dark:border-gray-700 pt-6">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Timezone
          </label>
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
            Used to bucket the dashboard agenda into Morning / Afternoon /
            Evening for your local wall clock. Use an IANA name (e.g.
            <code className="mx-1 rounded bg-gray-100 px-1 dark:bg-gray-700">America/New_York</code>).
          </p>
          <div className="flex gap-2">
            <input
              type="text"
              value={form.timezone}
              onChange={(e) => setForm({ ...form, timezone: e.target.value })}
              onBlur={() => {
                if (isAdmin) saveMutation.mutate(form);
              }}
              placeholder="America/New_York"
              className="flex-1 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-3 text-base text-gray-900 dark:text-gray-100 min-h-[44px]"
              disabled={!isAdmin}
            />
            {isAdmin && (
              <button
                type="button"
                onClick={() => {
                  const detected =
                    (typeof Intl !== "undefined" &&
                      Intl.DateTimeFormat().resolvedOptions().timeZone) ||
                    "UTC";
                  const updated = { ...form, timezone: detected };
                  setForm(updated);
                  saveMutation.mutate(updated);
                }}
                className="rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 px-4 py-3 text-sm font-medium text-gray-700 dark:text-gray-300 min-h-[44px]"
              >
                Use this device
              </button>
            )}
          </div>
        </div>
      </section>

       {/* Integrations */}
      <section className="rounded-2xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          🌤️ Weather
        </h3>
        <div className="space-y-4">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Enter your location coordinates for weather on the dashboard, or use the button below to auto-detect.
          </p>
          <button
            type="button"
            onClick={() => {
              if (!navigator.geolocation) {
                alert("Geolocation is not supported by this browser.");
                return;
              }
              navigator.geolocation.getCurrentPosition(
                (pos) => {
                  setForm((prev) => ({
                    ...prev,
                    weather_lat: Math.round(pos.coords.latitude * 10000) / 10000,
                    weather_lon: Math.round(pos.coords.longitude * 10000) / 10000,
                  }));
                },
                (err) => {
                  alert(`Could not get location: ${err.message}`);
                },
              );
            }}
            className="w-full rounded-lg bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 px-4 py-3 text-sm font-medium text-blue-700 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-900/50 transition-colors min-h-[44px]"
          >
            📍 Use My Location
          </button>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Latitude
              </label>
              <input
                type="number"
                step="any"
                placeholder="e.g. 40.7128"
                value={form.weather_lat ?? ""}
                onChange={(e) =>
                  setForm((prev) => ({
                    ...prev,
                    weather_lat: e.target.value ? parseFloat(e.target.value) : null,
                  }))
                }
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-3 text-base text-gray-900 dark:text-gray-100 min-h-[44px]"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Longitude
              </label>
              <input
                type="number"
                step="any"
                placeholder="e.g. -74.0060"
                value={form.weather_lon ?? ""}
                onChange={(e) =>
                  setForm((prev) => ({
                    ...prev,
                    weather_lon: e.target.value ? parseFloat(e.target.value) : null,
                  }))
                }
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-3 text-base text-gray-900 dark:text-gray-100 min-h-[44px]"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Temperature Units
            </label>
            <div className="flex gap-2">
              {(["imperial", "metric"] as const).map((u) => (
                <button
                  key={u}
                  type="button"
                  onClick={() =>
                    setForm((prev) => ({ ...prev, weather_units: u }))
                  }
                  className={`rounded-lg px-4 py-2 text-sm font-medium min-h-[44px] transition-colors ${
                    form.weather_units === u
                      ? "bg-blue-600 text-white"
                      : "bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600"
                  }`}
                >
                  {u === "imperial" ? "°F (Imperial)" : "°C (Metric)"}
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Screensaver Settings */}
      <section className="rounded-2xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          🌙 Screensaver
        </h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Idle Timeout
            </label>
            <div className="flex items-center gap-3">
              <input
                type="range"
                min={1}
                max={30}
                value={form.screensaver_timeout_minutes}
                onChange={(e) =>
                  setForm((prev) => ({
                    ...prev,
                    screensaver_timeout_minutes: parseInt(e.target.value),
                  }))
                }
                className="flex-1"
              />
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300 w-16 text-right tabular-nums">
                {form.screensaver_timeout_minutes} min
              </span>
            </div>
            <p className="text-xs text-gray-400 mt-1">
              How long before the screensaver activates
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Photo Transition Speed
            </label>
            <div className="flex items-center gap-3">
              <input
                type="range"
                min={3}
                max={60}
                step={1}
                value={form.screensaver_transition_seconds}
                onChange={(e) =>
                  setForm((prev) => ({
                    ...prev,
                    screensaver_transition_seconds: parseInt(e.target.value),
                  }))
                }
                className="flex-1"
              />
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300 w-16 text-right tabular-nums">
                {form.screensaver_transition_seconds}s
              </span>
            </div>
            <p className="text-xs text-gray-400 mt-1">
              Seconds between photo transitions
            </p>
          </div>
        </div>
      </section>

      {/* Screensaver Photos */}
      <ScreensaverPhotosSection householdId={householdId} />

      {/* Vacation Mode (Phase C parental override) */}
      <VacationModeSection householdId={householdId} />

      {/* Holiday calendar source for school-day detection */}
      <HolidayCalendarSection householdId={householdId} />

      {/* School-day calendar (snow days, in-service days, etc.) */}
      <SchoolClosuresSection householdId={householdId} />

      {/* Calendar & Outlook Integrations */}
      <section className="rounded-2xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          🔗 Integrations
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {/* Google Calendar */}
          <div className="flex items-center justify-between rounded-xl border border-gray-200 dark:border-gray-700 p-4">
            <div className="flex items-center gap-3">
              <span className="text-2xl">📅</span>
              <div>
                <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  Google Calendar
                </div>
                <div
                  className={`text-xs ${
                    integrationStatus?.google
                      ? "text-green-600 dark:text-green-400"
                      : "text-gray-400 dark:text-gray-500"
                  }`}
                >
                  {integrationStatus?.google ? "Connected" : "Disconnected"}
                </div>
              </div>
            </div>
            <button
              type="button"
              onClick={connectGoogle}
              className={`rounded-lg px-3 py-2 text-xs font-medium min-h-[44px] transition-colors ${
                integrationStatus?.google
                  ? "bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400"
                  : "bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 hover:bg-blue-200"
              }`}
            >
              {integrationStatus?.google ? "Connected" : "Connect"}
            </button>
          </div>

          {/* Microsoft / Outlook */}
          <div className="flex items-center justify-between rounded-xl border border-gray-200 dark:border-gray-700 p-4">
            <div className="flex items-center gap-3">
              <span className="text-2xl">📧</span>
              <div>
                <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  Outlook
                </div>
                <div
                  className={`text-xs ${
                    integrationStatus?.microsoft
                      ? "text-green-600 dark:text-green-400"
                      : "text-gray-400 dark:text-gray-500"
                  }`}
                >
                  {integrationStatus?.microsoft ? "Connected" : "Disconnected"}
                </div>
              </div>
            </div>
            <button
              type="button"
              onClick={connectMicrosoft}
              className={`rounded-lg px-3 py-2 text-xs font-medium min-h-[44px] transition-colors ${
                integrationStatus?.microsoft
                  ? "bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400"
                  : "bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 hover:bg-blue-200"
              }`}
            >
              {integrationStatus?.microsoft ? "Connected" : "Connect"}
            </button>
          </div>

          {/* iCal Subscription (lightweight, no OAuth) */}
          <div className="flex items-center justify-between rounded-xl border border-gray-200 dark:border-gray-700 p-4 sm:col-span-2">
            <div className="flex items-center gap-3">
              <span className="text-2xl">🔗</span>
              <div>
                <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  iCal Subscription
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  Read-only. Works with Google Calendar's <em>Secret address in iCal format</em>,
                  Apple iCloud, Outlook web — anything that publishes a <code>.ics</code> URL.
                </div>
              </div>
            </div>
            <button
              type="button"
              onClick={() =>
                setIcalForm({
                  open: true,
                  name: "",
                  url: "",
                  error: null,
                  errorKind: null,
                  submitting: false,
                })
              }
              className="rounded-lg px-3 py-2 text-xs font-medium min-h-[44px] bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 hover:bg-blue-200 transition-colors whitespace-nowrap"
            >
              + Add URL
            </button>
          </div>

          {/* Subscribed iCal calendars */}
          {icalCalendars.length > 0 && (
            <div className="sm:col-span-2 space-y-2">
              <div className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mt-2">
                Subscribed calendars
              </div>
              {icalCalendars.map((cal) => (
                <div
                  key={cal.id}
                  className="flex items-center justify-between rounded-lg border border-gray-200 dark:border-gray-700 px-4 py-2 text-sm"
                >
                  <div className="min-w-0 flex-1">
                    <div className="font-medium truncate text-gray-900 dark:text-gray-100">
                      {cal.name}
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      {cal.last_synced_at
                        ? `Last synced ${new Date(cal.last_synced_at).toLocaleString()}`
                        : "Not yet synced"}
                    </div>
                  </div>
                  <div className="flex gap-2 ml-3">
                    <button
                      type="button"
                      onClick={() => syncIcal(cal.id)}
                      className="rounded-md px-2.5 py-1.5 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-600"
                    >
                      Sync now
                    </button>
                    <button
                      type="button"
                      onClick={() => unsubscribeIcal(cal.id)}
                      className="rounded-md px-2.5 py-1.5 text-xs text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30"
                    >
                      Remove
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* iCal subscribe modal */}
      {icalForm.open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          onClick={() => !icalForm.submitting && setIcalForm((f) => ({ ...f, open: false }))}
        >
          <div
            className="w-full max-w-lg rounded-2xl bg-white dark:bg-gray-800 p-6 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
              Subscribe to a calendar
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              Paste a <code>.ics</code> URL. For Google Calendar: open the calendar's settings →
              <em> Integrate calendar</em> → copy the <strong>Secret address in iCal format</strong>.
            </p>

            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Calendar name
            </label>
            <input
              type="text"
              value={icalForm.name}
              onChange={(e) => setIcalForm((f) => ({ ...f, name: e.target.value }))}
              placeholder="Mom's Google Calendar"
              className="w-full mb-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-100"
              autoFocus
            />

            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              iCal URL
            </label>
            <input
              type="url"
              value={icalForm.url}
              onChange={(e) => setIcalForm((f) => ({ ...f, url: e.target.value }))}
              placeholder="https://calendar.google.com/calendar/ical/.../basic.ics"
              className="w-full mb-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 font-mono"
            />

            {icalForm.error && (
              <div
                className={
                  icalForm.errorKind === "duplicate"
                    ? "mb-3 rounded-lg bg-amber-50 dark:bg-amber-900/30 text-amber-800 dark:text-amber-200 border border-amber-200 dark:border-amber-700/50 px-3 py-2 text-sm"
                    : "mb-3 rounded-lg bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300 px-3 py-2 text-sm"
                }
                role={icalForm.errorKind === "duplicate" ? "status" : "alert"}
              >
                {icalForm.errorKind === "duplicate" ? (
                  <>
                    <strong className="font-semibold">Already connected. </strong>
                    {icalForm.error}
                  </>
                ) : (
                  icalForm.error
                )}
              </div>
            )}

            <div className="flex justify-end gap-2 mt-2">
              <button
                type="button"
                disabled={icalForm.submitting}
                onClick={() => setIcalForm((f) => ({ ...f, open: false }))}
                className="rounded-lg px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={
                  icalForm.submitting ||
                  !icalForm.name.trim() ||
                  !icalForm.url.trim()
                }
                onClick={submitIcal}
                className="rounded-lg px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
              >
                {icalForm.submitting ? "Validating…" : "Subscribe"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* System */}
      <section className="rounded-2xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          ⚙️ System
        </h3>
        <div className="space-y-4">
          <div className="text-sm text-gray-600 dark:text-gray-400">
            <p>
              <span className="font-medium text-gray-900 dark:text-gray-100">
                Hestia
              </span>{" "}
              v0.1.0
            </p>
            <p className="mt-1">
              A warm family display dashboard, named after the Greek goddess of
              hearth and home.
            </p>
          </div>
          <div className="flex gap-3">
            <button
              type="button"
              className="rounded-xl bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 font-medium py-3 px-4 min-h-[44px] text-sm transition-colors"
            >
              Backup Data
            </button>
            <button
              type="button"
              className="rounded-xl bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 font-medium py-3 px-4 min-h-[44px] text-sm transition-colors"
            >
              Restore Data
            </button>
          </div>
        </div>
      </section>

      {/* Save button */}
      <div className="sticky bottom-4">
        <button
          onClick={handleSave}
          disabled={saveMutation.isPending || !isAdmin}
          className="w-full rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold py-4 px-6 min-h-[44px] shadow-lg disabled:opacity-50 transition-colors"
        >
          {!isAdmin
            ? "🔒 Admin Required"
            : saveMutation.isPending
              ? "Saving..."
              : "Save Settings"}
        </button>
        {showSaved && (
          <p className="text-center text-sm text-green-600 dark:text-green-400 mt-2">
            Settings saved!
          </p>
        )}
      </div>
    </div>
  );
}

/* ------------ Screensaver Photos sub-component ------------ */

function ScreensaverPhotosSection({ householdId }: { householdId: string | null }) {
  const queryClient = useQueryClient();
  const [newUrl, setNewUrl] = useState("");
  const [newCaption, setNewCaption] = useState("");
  const [uploading, setUploading] = useState(false);

  const { data: photoList = [] } = useQuery<{ id: string; url: string; caption: string | null; sort_order: number }[]>({
    queryKey: ["photos", householdId],
    queryFn: () => photosApi.getAll(householdId!).then((r) => r.data),
    enabled: !!householdId,
  });

  const addMutation = useMutation({
    mutationFn: (data: { url: string; caption?: string; household_id: string }) =>
      photosApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["photos"] });
      setNewUrl("");
      setNewCaption("");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => photosApi.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["photos"] }),
  });

  const handleAdd = () => {
    if (!newUrl.trim() || !householdId) return;
    addMutation.mutate({
      url: newUrl.trim(),
      caption: newCaption.trim() || undefined,
      household_id: householdId,
    });
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !householdId) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("household_id", householdId);
      formData.append("caption", newCaption.trim());
      await photosApi.upload(formData);
      queryClient.invalidateQueries({ queryKey: ["photos"] });
      setNewCaption("");
    } catch {
      // handle error silently
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  return (
    <section className="rounded-2xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
        🖼️ Screensaver Photos
      </h3>
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
        Add photo URLs to display in the screensaver slideshow when the display is idle.
      </p>

      {/* Add photo form */}
      <div className="space-y-3 mb-4">
        {/* File upload */}
        <div>
          <label className="flex items-center justify-center gap-2 rounded-lg border-2 border-dashed border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700/50 px-4 py-3 text-sm font-medium text-gray-600 dark:text-gray-400 cursor-pointer hover:border-blue-400 hover:text-blue-600 transition min-h-[44px]">
            {uploading ? (
              "Uploading…"
            ) : (
              <>📷 Upload Photo</>
            )}
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp,image/gif"
              className="hidden"
              onChange={handleFileUpload}
              disabled={uploading}
            />
          </label>
        </div>

        {/* OR divider */}
        <div className="flex items-center gap-3">
          <div className="flex-1 border-t border-gray-200 dark:border-gray-700" />
          <span className="text-xs text-gray-400">or add by URL</span>
          <div className="flex-1 border-t border-gray-200 dark:border-gray-700" />
        </div>

        {/* URL input */}
        <input
          type="url"
          placeholder="Photo URL (https://...)"
          value={newUrl}
          onChange={(e) => setNewUrl(e.target.value)}
          className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100"
        />
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Caption (optional)"
            value={newCaption}
            onChange={(e) => setNewCaption(e.target.value)}
            className="flex-1 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100"
          />
          <button
            type="button"
            onClick={handleAdd}
            disabled={!newUrl.trim() || addMutation.isPending}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 min-h-[36px]"
          >
            Add
          </button>
        </div>
      </div>

      {/* Photo list */}
      {photoList.length === 0 ? (
        <p className="text-sm text-gray-400 italic">No photos yet.</p>
      ) : (
        <ul className="space-y-2">
          {photoList.map((photo) => (
            <li
              key={photo.id}
              className="flex items-center gap-3 rounded-lg border border-gray-200 dark:border-gray-700 p-2"
            >
              <img
                src={photo.url}
                alt={photo.caption ?? "Photo"}
                className="h-12 w-12 rounded object-cover flex-shrink-0"
              />
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-900 dark:text-gray-100 truncate">
                  {photo.caption || photo.url}
                </p>
              </div>
              <button
                type="button"
                onClick={() => deleteMutation.mutate(photo.id)}
                className="text-red-500 hover:text-red-700 text-sm p-1"
                aria-label="Remove photo"
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}


// ── Vacation Mode (Phase C: household-wide pause for opt-in routines) ────────

import {
  routineOverrides as overridesApiVM,
  type RoutineOverride as RoutineOverrideVM,
  schoolClosures as closuresApi,
  type SchoolClosure as SchoolClosureT,
} from "@/api/endpoints";

function VacationModeSection({ householdId }: { householdId: string | null }) {
  const queryClient = useQueryClient();
  const todayIso = new Date().toISOString().slice(0, 10);
  const [start, setStart] = useState(todayIso);
  const [end, setEnd] = useState("");
  const [reason, setReason] = useState("");

  const { data: overrides = [] } = useQuery<RoutineOverrideVM[]>({
    queryKey: ["routine-overrides", householdId, "household-wide"],
    queryFn: async () =>
      (await overridesApiVM.list(householdId!)).data.filter(
        (o) => o.routine_id === null,
      ),
    enabled: !!householdId,
  });

  const createMutation = useMutation({
    mutationFn: () =>
      overridesApiVM.create({
        routine_id: null,
        kind: "pause",
        start_date: start,
        end_date: end || null,
        reason: reason || null,
      }),
    onSuccess: () => {
      setReason("");
      setEnd("");
      queryClient.invalidateQueries({ queryKey: ["routine-overrides"] });
      queryClient.invalidateQueries({ queryKey: ["routines"] });
    },
  });

  const cancelMutation = useMutation({
    mutationFn: (id: string) => overridesApiVM.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["routine-overrides"] });
      queryClient.invalidateQueries({ queryKey: ["routines"] });
    },
  });

  const active = overrides.filter(
    (o) => o.start_date <= todayIso && (o.end_date === null || o.end_date >= todayIso),
  );

  return (
    <section className="rounded-2xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
        🏝️ Vacation Mode
      </h3>
      <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
        Pause every routine that's marked "pausable on vacation" for a date
        range. Routines flagged as not-pausable (medications, allergy meds,
        etc.) keep running.
      </p>

      {active.length > 0 && (
        <div className="mb-4 space-y-2">
          {active.map((o) => (
            <div
              key={o.id}
              className="flex items-center justify-between rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 px-3 py-2"
            >
              <div className="text-sm text-amber-900 dark:text-amber-200">
                <strong>Active:</strong> {o.start_date}
                {o.end_date ? ` → ${o.end_date}` : " (indefinite)"}
                {o.reason && <span className="ml-2 italic">— {o.reason}</span>}
              </div>
              <button
                onClick={() => cancelMutation.mutate(o.id)}
                className="text-sm font-semibold text-amber-700 dark:text-amber-300 hover:underline"
              >
                End now
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <label className="text-sm text-gray-700 dark:text-gray-300">
          Start
          <input
            type="date"
            value={start}
            min={todayIso}
            onChange={(e) => setStart(e.target.value)}
            className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2"
          />
        </label>
        <label className="text-sm text-gray-700 dark:text-gray-300">
          End (blank = indefinite)
          <input
            type="date"
            value={end}
            min={start}
            onChange={(e) => setEnd(e.target.value)}
            className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2"
          />
        </label>
        <label className="text-sm text-gray-700 dark:text-gray-300">
          Reason (optional)
          <input
            type="text"
            value={reason}
            placeholder="Beach week"
            onChange={(e) => setReason(e.target.value)}
            className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2"
          />
        </label>
      </div>
      <div className="mt-4 flex justify-end">
        <button
          disabled={!householdId || createMutation.isPending}
          onClick={() => createMutation.mutate()}
          className="touch-target rounded-xl bg-amber-600 px-5 py-2 font-semibold text-white shadow transition hover:opacity-90 active:scale-95 disabled:opacity-50"
        >
          Start Vacation Mode
        </button>
      </div>
    </section>
  );
}


// ── School Closures (snow days, district holidays, in-service days) ──────────

function SchoolClosuresSection({ householdId }: { householdId: string | null }) {
  const queryClient = useQueryClient();
  const todayIso = new Date().toISOString().slice(0, 10);
  const [date, setDate] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data: closures = [] } = useQuery<SchoolClosureT[]>({
    queryKey: ["school-closures", householdId],
    queryFn: async () =>
      (await closuresApi.list(householdId!, { start_date: todayIso })).data,
    enabled: !!householdId,
  });

  const createMutation = useMutation({
    mutationFn: () =>
      closuresApi.create({
        household_id: householdId!,
        date,
        reason: reason || null,
      }),
    onSuccess: () => {
      setDate("");
      setReason("");
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["school-closures"] });
      queryClient.invalidateQueries({ queryKey: ["routines"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["splash"] });
    },
    onError: (err: unknown) => {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Could not add closure";
      setError(typeof detail === "string" ? detail : "Could not add closure");
    },
  });

  const removeMutation = useMutation({
    mutationFn: (id: string) => closuresApi.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["school-closures"] });
      queryClient.invalidateQueries({ queryKey: ["routines"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["splash"] });
    },
  });

  return (
    <section className="rounded-2xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
        🎒 School Closures
      </h3>
      <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
        Mark snow days, in-service days, and district holidays. Routine
        steps tagged <em>"Only on school days"</em> (e.g. "pack backpack")
        are hidden on these dates and on weekends + US federal holidays.
      </p>

      {closures.length > 0 && (
        <ul className="mb-4 divide-y divide-gray-200 dark:divide-gray-700 rounded-lg border border-gray-200 dark:border-gray-700">
          {closures.map((c) => (
            <li
              key={c.id}
              className="flex items-center justify-between px-3 py-2 text-sm"
            >
              <div className="text-gray-800 dark:text-gray-200">
                <strong>{c.date}</strong>
                {c.reason && (
                  <span className="ml-2 italic text-gray-500 dark:text-gray-400">
                    — {c.reason}
                  </span>
                )}
              </div>
              <button
                onClick={() => removeMutation.mutate(c.id)}
                className="text-xs font-semibold text-red-600 hover:underline dark:text-red-400"
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}

      {error && (
        <div className="mb-3 rounded-lg bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300 px-3 py-2 text-sm">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <label className="text-sm text-gray-700 dark:text-gray-300">
          Date
          <input
            type="date"
            value={date}
            min={todayIso}
            onChange={(e) => setDate(e.target.value)}
            className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2"
          />
        </label>
        <label className="sm:col-span-2 text-sm text-gray-700 dark:text-gray-300">
          Reason (optional)
          <input
            type="text"
            value={reason}
            placeholder="Snow day"
            onChange={(e) => setReason(e.target.value)}
            className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2"
          />
        </label>
      </div>
      <div className="mt-4 flex justify-end">
        <button
          disabled={!householdId || !date || createMutation.isPending}
          onClick={() => createMutation.mutate()}
          className="touch-target rounded-xl bg-blue-600 px-5 py-2 font-semibold text-white shadow transition hover:opacity-90 active:scale-95 disabled:opacity-50"
        >
          Add Closure
        </button>
      </div>
    </section>
  );
}


// ── Holiday Calendar (drives school_day_only step filter) ─────────────────────

function HolidayCalendarSection({ householdId }: { householdId: string | null }) {
  const queryClient = useQueryClient();

  const { data: settingsData } = useQuery({
    queryKey: ["settings", householdId],
    queryFn: async () => (await admin.getSettings(householdId!)).data,
    enabled: !!householdId,
  });

  const { data: options } = useQuery({
    queryKey: ["admin-holiday-options"],
    queryFn: async () => (await admin.getHolidayOptions()).data,
  });

  const currentCountry =
    (settingsData as { holiday_country?: string } | undefined)?.holiday_country ?? "US";
  const currentSubdiv =
    (settingsData as { holiday_subdiv?: string | null } | undefined)?.holiday_subdiv ?? "";

  const [country, setCountry] = useState<string>(currentCountry);
  const [subdiv, setSubdiv] = useState<string>(currentSubdiv ?? "");
  const [savedAt, setSavedAt] = useState<number | null>(null);

  // Resync local state when the server values arrive / change.
  useEffect(() => {
    setCountry(currentCountry);
    setSubdiv(currentSubdiv ?? "");
  }, [currentCountry, currentSubdiv]);

  const countryNames = useMemo(() => {
    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const dn = new (Intl as any).DisplayNames(["en"], { type: "region" });
      return (code: string) => dn.of(code) ?? code;
    } catch {
      return (code: string) => code;
    }
  }, []);

  const saveMutation = useMutation({
    mutationFn: () =>
      admin.updateSettings(householdId!, {
        holiday_country: country,
        holiday_subdiv: subdiv ? subdiv : null,
      }),
    onSuccess: () => {
      setSavedAt(Date.now());
      queryClient.invalidateQueries({ queryKey: ["settings", householdId] });
      queryClient.invalidateQueries({ queryKey: ["routines"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["splash"] });
    },
  });

  const subdivOptions = options?.subdivisions?.[country] ?? [];
  const dirty =
    country !== currentCountry || (subdiv || null) !== (currentSubdiv || null);

  return (
    <section className="rounded-2xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
        🗓️ Holiday Calendar
      </h3>
      <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
        Routine steps marked <em>"Only on school days"</em> are hidden on
        the holidays for this country (and optional state/region).
        Defaults to US federal holidays.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <label className="text-sm text-gray-700 dark:text-gray-300">
          Country
          <select
            value={country}
            onChange={(e) => {
              setCountry(e.target.value);
              setSubdiv("");
            }}
            className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2"
          >
            {(options?.countries ?? [country]).map((c) => (
              <option key={c} value={c}>
                {countryNames(c)} ({c})
              </option>
            ))}
          </select>
        </label>

        <label className="text-sm text-gray-700 dark:text-gray-300">
          State / region
          <select
            value={subdiv}
            onChange={(e) => setSubdiv(e.target.value)}
            disabled={subdivOptions.length === 0}
            className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 disabled:opacity-50"
          >
            <option value="">
              {subdivOptions.length === 0
                ? "(no subdivisions)"
                : "National only"}
            </option>
            {subdivOptions.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="mt-4 flex items-center justify-end gap-3">
        {savedAt && !dirty && (
          <span className="text-xs text-emerald-600 dark:text-emerald-400">
            Saved
          </span>
        )}
        <button
          disabled={!householdId || !dirty || saveMutation.isPending}
          onClick={() => saveMutation.mutate()}
          className="touch-target rounded-xl bg-blue-600 px-5 py-2 font-semibold text-white shadow transition hover:opacity-90 active:scale-95 disabled:opacity-50"
        >
          {saveMutation.isPending ? "Saving…" : "Save"}
        </button>
      </div>
    </section>
  );
}
