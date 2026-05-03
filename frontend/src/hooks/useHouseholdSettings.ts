import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { admin } from "@/api/endpoints";
import { useHouseholdStore } from "@/stores/householdStore";
import { useThemeStore } from "@/stores/themeStore";
import type { SplashCalendarMode, SplashMode } from "@/types/splash";

interface ModulesEnabled {
  calendar: boolean;
  routines: boolean;
  lists: boolean;
  meals: boolean;
  weather: boolean;
  screensaver: boolean;
  messages: boolean;
  notifications: boolean;
  rewards: boolean;
}

export interface HouseholdSettings {
  name: string;
  theme: "light" | "dark";
  accent_color: string;
  modules_enabled: ModulesEnabled;
  // Pre-login splash + privacy policy. Replaces the deprecated
  // post-login `privacy_mode` boolean (PRD §2.12 / Hestia v2.2).
  splash_mode: SplashMode;
  splash_alternating_seconds: number;
  splash_calendar_mode: SplashCalendarMode;
  splash_agenda_max_days: number;
  splash_show_routines: boolean;
  splash_show_meals: boolean;
  splash_show_weather: boolean;
  splash_show_messages: boolean;
  time_format: "12h" | "24h";
  weather_lat: number | null;
  weather_lon: number | null;
  weather_units: string;
  screensaver_timeout_minutes: number;
  screensaver_transition_seconds: number;
}

const DEFAULT_MODULES: ModulesEnabled = {
  calendar: true,
  routines: true,
  lists: true,
  meals: true,
  weather: true,
  screensaver: true,
  messages: true,
  notifications: true,
  rewards: true,
};

export function useHouseholdSettings() {
  const householdId = useHouseholdStore((s) => s.householdId);

  const query = useQuery<HouseholdSettings>({
    queryKey: ["settings", householdId],
    queryFn: async () => {
      const res = await admin.getSettings(householdId!);
      return res.data as HouseholdSettings;
    },
    enabled: !!householdId,
    staleTime: 5_000,
    refetchOnWindowFocus: true,
  });

  // Sync theme store with server settings on load
  useEffect(() => {
    if (query.data) {
      const { theme, accent_color } = query.data;
      const store = useThemeStore.getState();
      if (store.theme !== theme) {
        store.setTheme(theme);
      }
      if (store.accentColor !== accent_color) {
        store.setAccentColor(accent_color);
      }
    }
  }, [query.data]);

  return {
    settings: query.data,
    isLoading: query.isLoading,
    modulesEnabled: query.data?.modules_enabled ?? DEFAULT_MODULES,
    timeFormat: (query.data?.time_format ?? "12h") as "12h" | "24h",
  };
}
