import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { admin } from "@/api/endpoints";
import { useHouseholdStore } from "@/stores/householdStore";
import { useThemeStore } from "@/stores/themeStore";

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
  privacy_mode: boolean;
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
    privacyMode: query.data?.privacy_mode ?? false,
  };
}
