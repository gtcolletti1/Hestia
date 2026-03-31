import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import client from "@/api/client";
import { useHouseholdStore } from "@/stores/householdStore";
import { getTheme, setTheme, type Theme } from "@/utils/theme";

interface HouseholdSettings {
  household_name: string;
  theme: Theme;
  accent_color: string;
  modules: {
    calendar: boolean;
    routines: boolean;
    lists: boolean;
    meals: boolean;
  };
  privacy_mode: boolean;
}

interface Integration {
  id: string;
  name: string;
  icon: string;
  connected: boolean;
}

const DEFAULT_SETTINGS: HouseholdSettings = {
  household_name: "My Family",
  theme: getTheme(),
  accent_color: "#3B82F6",
  modules: {
    calendar: true,
    routines: true,
    lists: true,
    meals: true,
  },
  privacy_mode: false,
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

const INITIAL_INTEGRATIONS: Integration[] = [
  { id: "google-calendar", name: "Google Calendar", icon: "📅", connected: false },
  { id: "outlook", name: "Outlook", icon: "📧", connected: false },
  { id: "ical", name: "iCal", icon: "🗓️", connected: false },
  { id: "todoist", name: "Todoist", icon: "✅", connected: false },
  { id: "ms-todo", name: "MS To Do", icon: "☑️", connected: false },
  { id: "weather", name: "Weather", icon: "🌤️", connected: false },
];

export default function SettingsPanel() {
  const householdId = useHouseholdStore((s) => s.householdId);
  const queryClient = useQueryClient();

  const { data: settings } = useQuery({
    queryKey: ["settings", householdId],
    queryFn: () =>
      client
        .get<HouseholdSettings>(`/admin/settings`, {
          params: { household_id: householdId },
        })
        .then((r) => r.data)
        .catch(() => DEFAULT_SETTINGS),
    enabled: !!householdId,
    initialData: DEFAULT_SETTINGS,
  });

  const [form, setForm] = useState<HouseholdSettings>(settings);
  const [integrations, setIntegrations] =
    useState<Integration[]>(INITIAL_INTEGRATIONS);

  useEffect(() => {
    setForm(settings);
  }, [settings]);

  const saveMutation = useMutation({
    mutationFn: (data: HouseholdSettings) =>
      client.put(`/admin/settings`, {
        ...data,
        household_id: householdId,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings"] });
    },
  });

  const handleSave = () => {
    saveMutation.mutate(form);
  };

  const updateModules = (
    key: keyof HouseholdSettings["modules"],
    value: boolean,
  ) => {
    setForm((prev) => ({
      ...prev,
      modules: { ...prev.modules, [key]: value },
    }));
  };

  const handleThemeChange = (theme: Theme) => {
    setForm((prev) => ({ ...prev, theme }));
    setTheme(theme);
  };

  const toggleIntegration = (id: string) => {
    setIntegrations((prev) =>
      prev.map((i) => (i.id === id ? { ...i, connected: !i.connected } : i)),
    );
  };

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
        Settings
      </h2>

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
            value={form.household_name}
            onChange={(e) =>
              setForm((prev) => ({
                ...prev,
                household_name: e.target.value,
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
                  onClick={() =>
                    setForm((prev) => ({ ...prev, accent_color: c }))
                  }
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
            Object.entries(form.modules) as [
              keyof HouseholdSettings["modules"],
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

      {/* Privacy */}
      <section className="rounded-2xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          🔒 Privacy
        </h3>
        <div className="flex items-center justify-between">
          <div>
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Privacy Mode
            </span>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Hide event details on wall display
            </p>
          </div>
          <button
            type="button"
            onClick={() =>
              setForm((prev) => ({
                ...prev,
                privacy_mode: !prev.privacy_mode,
              }))
            }
            className={`relative inline-flex h-7 w-12 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors min-h-[44px] items-center ${
              form.privacy_mode
                ? "bg-blue-600"
                : "bg-gray-300 dark:bg-gray-600"
            }`}
            role="switch"
            aria-checked={form.privacy_mode}
          >
            <span
              className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${
                form.privacy_mode ? "translate-x-5" : "translate-x-0.5"
              }`}
            />
          </button>
        </div>
      </section>

      {/* Integrations */}
      <section className="rounded-2xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          🔗 Integrations
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {integrations.map((integration) => (
            <div
              key={integration.id}
              className="flex items-center justify-between rounded-xl border border-gray-200 dark:border-gray-700 p-4"
            >
              <div className="flex items-center gap-3">
                <span className="text-2xl">{integration.icon}</span>
                <div>
                  <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {integration.name}
                  </div>
                  <div
                    className={`text-xs ${
                      integration.connected
                        ? "text-green-600 dark:text-green-400"
                        : "text-gray-400 dark:text-gray-500"
                    }`}
                  >
                    {integration.connected ? "Connected" : "Disconnected"}
                  </div>
                </div>
              </div>
              <button
                type="button"
                onClick={() => toggleIntegration(integration.id)}
                className={`rounded-lg px-3 py-2 text-xs font-medium min-h-[44px] transition-colors ${
                  integration.connected
                    ? "bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 hover:bg-red-200"
                    : "bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 hover:bg-blue-200"
                }`}
              >
                {integration.connected ? "Disconnect" : "Connect"}
              </button>
            </div>
          ))}
        </div>
      </section>

      {/* System */}
      <section className="rounded-2xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          ⚙️ System
        </h3>
        <div className="space-y-4">
          <div className="text-sm text-gray-600 dark:text-gray-400">
            <p>
              <span className="font-medium text-gray-900 dark:text-gray-100">
                Family Hub
              </span>{" "}
              v0.1.0
            </p>
            <p className="mt-1">
              A family display dashboard for organizing your household.
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
          disabled={saveMutation.isPending}
          className="w-full rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold py-4 px-6 min-h-[44px] shadow-lg disabled:opacity-50 transition-colors"
        >
          {saveMutation.isPending ? "Saving..." : "Save Settings"}
        </button>
        {saveMutation.isSuccess && (
          <p className="text-center text-sm text-green-600 dark:text-green-400 mt-2">
            Settings saved!
          </p>
        )}
      </div>
    </div>
  );
}
