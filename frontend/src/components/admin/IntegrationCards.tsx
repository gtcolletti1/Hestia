import { useCallback } from "react";

/* -------------------------------------------------------------------------- */
/*  Types                                                                     */
/* -------------------------------------------------------------------------- */

type Provider = "google" | "microsoft" | "ical" | "todoist" | "weather";

interface Integration {
  provider: Provider;
  connected: boolean;
  email?: string;
  /** IDs of calendars currently being synced (calendar providers only). */
  syncedCalendarIds?: string[];
  availableCalendars?: { id: string; name: string }[];
}

interface IntegrationCardsProps {
  integrations: Integration[];
  onConnect: (provider: Provider) => void;
  onDisconnect: (provider: Provider) => void;
  onToggleCalendar?: (provider: Provider, calendarId: string, enabled: boolean) => void;
}

/* -------------------------------------------------------------------------- */
/*  Constants                                                                 */
/* -------------------------------------------------------------------------- */

const SERVICE_META: Record<Provider, { label: string; emoji: string }> = {
  google: { label: "Google Calendar", emoji: "📆" },
  microsoft: { label: "Outlook Calendar", emoji: "📅" },
  ical: { label: "iCal / Apple Calendar", emoji: "🍎" },
  todoist: { label: "Todoist", emoji: "✅" },
  weather: { label: "Weather", emoji: "🌤️" },
};

/* -------------------------------------------------------------------------- */
/*  Single card                                                               */
/* -------------------------------------------------------------------------- */

function IntegrationCard({
  integration,
  onConnect,
  onDisconnect,
  onToggleCalendar,
}: {
  integration: Integration;
  onConnect: (p: Provider) => void;
  onDisconnect: (p: Provider) => void;
  onToggleCalendar?: (p: Provider, calId: string, enabled: boolean) => void;
}) {
  const { provider, connected, email, availableCalendars, syncedCalendarIds } =
    integration;
  const meta = SERVICE_META[provider];

  const handleConnect = useCallback(() => onConnect(provider), [onConnect, provider]);
  const handleDisconnect = useCallback(
    () => onDisconnect(provider),
    [onDisconnect, provider],
  );

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 p-5 flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-center gap-3">
        <span className="text-3xl">{meta.emoji}</span>
        <div className="flex-1">
          <h3 className="font-semibold">{meta.label}</h3>
          {connected ? (
            <span className="text-sm text-green-600 dark:text-green-400">
              Connected{email ? ` — ${email}` : ""}
            </span>
          ) : (
            <span className="text-sm text-gray-400">Disconnected</span>
          )}
        </div>
      </div>

      {/* Calendar selection (only for connected calendar providers) */}
      {connected &&
        availableCalendars &&
        availableCalendars.length > 0 &&
        onToggleCalendar && (
          <div className="text-sm space-y-1">
            <p className="font-medium text-gray-600 dark:text-gray-300">
              Sync calendars:
            </p>
            {availableCalendars.map((cal) => {
              const checked = syncedCalendarIds?.includes(cal.id) ?? false;
              return (
                <label key={cal.id} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={(e) =>
                      onToggleCalendar(provider, cal.id, e.target.checked)
                    }
                    className="rounded"
                  />
                  <span>{cal.name}</span>
                </label>
              );
            })}
          </div>
        )}

      {/* Actions */}
      <div className="mt-auto pt-2">
        {connected ? (
          <button
            type="button"
            onClick={handleDisconnect}
            className="w-full rounded-lg border border-red-300 text-red-600 dark:border-red-700 dark:text-red-400 px-4 py-2 text-sm hover:bg-red-50 dark:hover:bg-red-950 transition"
          >
            Disconnect
          </button>
        ) : (
          <button
            type="button"
            onClick={handleConnect}
            className="w-full rounded-lg text-white px-4 py-2 text-sm transition"
            style={{ backgroundColor: "var(--color-accent, #3b82f6)" }}
          >
            Connect
          </button>
        )}
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/*  Grid wrapper                                                              */
/* -------------------------------------------------------------------------- */

export default function IntegrationCards({
  integrations,
  onConnect,
  onDisconnect,
  onToggleCalendar,
}: IntegrationCardsProps) {
  return (
    <section>
      <h2 className="text-xl font-bold mb-4">Integrations</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {integrations.map((integration) => (
          <IntegrationCard
            key={integration.provider}
            integration={integration}
            onConnect={onConnect}
            onDisconnect={onDisconnect}
            onToggleCalendar={onToggleCalendar}
          />
        ))}
      </div>
    </section>
  );
}
