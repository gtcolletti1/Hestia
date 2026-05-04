import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { format, parseISO } from "date-fns";
import { formatTime } from "@/utils/timeFormat";
import { dashboard, routines as routinesApi } from "@/api/endpoints";
import { useHouseholdStore } from "@/stores/householdStore";
import { useHouseholdSettings } from "@/hooks/useHouseholdSettings";
import WeatherWidget from "./WeatherWidget";
import MessagesWidget from "./MessagesWidget";
import LeaderboardWidget from "./LeaderboardWidget";
import NotificationBell from "./NotificationBell";
import RoutineStepper from "@/components/routines/RoutineStepper";
import type {
  DashboardData,
  AgendaBucket,
  MealPlan,
  DashboardRoutine,
  Routine,
} from "@/types";

// ── Helpers ──

function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

const MEAL_LABELS: Record<string, string> = {
  breakfast: "Breakfast",
  lunch: "Lunch",
  dinner: "Dinner",
  snack: "Snack",
};

// ── Skeleton helpers ──

function SkeletonLine({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded bg-gray-200 dark:bg-gray-700 ${className}`} />;
}

function SkeletonCard() {
  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3">
      <SkeletonLine className="h-4 w-1/3" />
      <SkeletonLine className="h-3 w-2/3" />
      <SkeletonLine className="h-3 w-1/2" />
    </div>
  );
}

// ── Sub-components ──

function AgendaSection({ buckets, timeFormat }: { buckets: AgendaBucket[]; timeFormat: "12h" | "24h" }) {
  const hasEvents = buckets.some((b) => b.events.length > 0);

  return (
    <section className="space-y-6">
      <h2 className="text-lg font-semibold">Today&apos;s Agenda</h2>

      {!hasEvents && (
        <p className="text-sm text-gray-400 dark:text-gray-500 italic">
          No events today
        </p>
      )}

      {buckets.map((bucket) => (
        <div key={bucket.bucket}>
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">
            {bucket.bucket}
          </h3>

          {bucket.events.length === 0 ? (
            <p className="text-sm text-gray-400 dark:text-gray-500 italic">
              No events
            </p>
          ) : (
            <ul className="space-y-2">
              {bucket.events.map((ev) => (
                <li
                  key={ev.id}
                  className="flex items-start gap-3 rounded-lg bg-white dark:bg-gray-800 p-3 shadow-sm min-h-[44px]"
                >
                  {ev.color && (
                    <span
                      className="mt-1.5 h-3 w-3 shrink-0 rounded-full"
                      style={{ backgroundColor: ev.color }}
                    />
                  )}
                  <div className="min-w-0 flex-1">
                    <p className="font-medium truncate">{ev.title}</p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {formatTime(parseISO(ev.start_time), "h:mm a", timeFormat)}
                      {" – "}
                      {formatTime(parseISO(ev.end_time), "h:mm a", timeFormat)}
                    </p>
                    {ev.profile_name && (
                      <p className="text-xs text-gray-400 dark:text-gray-500">
                        {ev.profile_name}
                      </p>
                    )}
                    {ev.location && (
                      <p className="text-sm text-gray-400 dark:text-gray-500 truncate">
                        📍 {ev.location}
                      </p>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </section>
  );
}

function RoutinesWidget({
  routines,
  allDone,
  onOpen,
}: {
  routines: DashboardRoutine[];
  allDone: boolean;
  onOpen: (routineId: string) => void;
}) {
  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3">
      <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
        Active Routines
      </h3>
      {routines.length === 0 ? (
        allDone ? (
          <div className="flex flex-col items-center text-center py-3">
            <div className="text-3xl" aria-hidden>🎉</div>
            <p className="mt-1 text-sm font-semibold text-emerald-700 dark:text-emerald-300">
              All done for now!
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Nothing left for this time block.
            </p>
          </div>
        ) : (
          <p className="text-sm text-gray-400 italic">
            Nothing scheduled for this time block.
          </p>
        )
      ) : (
        <ul className="space-y-2">
          {routines.map((r) => (
            <li key={r.id}>
              <button
                type="button"
                onClick={() => onOpen(r.id)}
                className="flex w-full items-center gap-3 min-h-[44px] rounded-lg px-2 py-1 text-left transition hover:bg-gray-50 active:bg-gray-100 dark:hover:bg-gray-800/60 dark:active:bg-gray-800"
                aria-label={`Open ${r.name} step list`}
              >
                <span className="text-xs font-semibold uppercase text-gray-400 w-16 shrink-0">
                  {r.time_block}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="font-medium truncate">{r.name}</p>
                  <p className="text-xs text-gray-400">
                    {r.step_count} step{r.step_count !== 1 ? "s" : ""}
                  </p>
                </div>
                {(r.streak_days ?? 0) > 0 && (
                  <span
                    className="inline-flex items-center gap-1 rounded-full bg-orange-100 px-2 py-0.5 text-xs font-semibold text-orange-700 dark:bg-orange-900/30 dark:text-orange-300"
                    title={`${r.streak_days}-day streak`}
                  >
                    🔥 {r.streak_days}
                  </span>
                )}
                <svg
                  className="h-4 w-4 shrink-0 text-gray-300 dark:text-gray-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 5l7 7-7 7"
                  />
                </svg>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function MealsWidget({ meals }: { meals: MealPlan[] }) {
  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3">
      <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
        Today&apos;s Meals
      </h3>
      {meals.length === 0 ? (
        <p className="text-sm text-gray-400 italic">No meals planned</p>
      ) : (
        <ul className="space-y-2">
          {meals.map((m) => (
            <li key={m.id} className="flex items-center gap-3 min-h-[44px]">
              <span className="text-xs font-semibold uppercase text-gray-400 w-16 shrink-0">
                {MEAL_LABELS[m.meal_type] ?? m.meal_type}
              </span>
              <span className="truncate">{m.title}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ListsWidget({ lists }: { lists: DashboardData["active_lists"] }) {
  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3">
      <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
        Lists
      </h3>
      {lists.length === 0 ? (
        <p className="text-sm text-gray-400 italic">No active lists</p>
      ) : (
        <ul className="space-y-3">
          {lists.map((l, i) => {
            const pct = l.item_count === 0 ? 0 : Math.round((l.checked_count / l.item_count) * 100);
            return (
              <li key={i}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium truncate">{l.name}</span>
                  <span className="text-xs text-gray-400 shrink-0 ml-2">
                    {l.checked_count}/{l.item_count}
                  </span>
                </div>
                <div className="w-full rounded-full bg-gray-200 dark:bg-gray-700 h-2">
                  <div
                    className="h-2 rounded-full bg-green-500 transition-all"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

// ── Main component ──

export default function DashboardHome() {
  const householdId = useHouseholdStore((s) => s.householdId);
  const { modulesEnabled, timeFormat } = useHouseholdSettings();
  const queryClient = useQueryClient();
  const [openRoutine, setOpenRoutine] = useState<Routine | null>(null);

  const { data, isLoading, isError } = useQuery<DashboardData>({
    queryKey: ["dashboard", householdId],
    queryFn: async () => {
      const res = await dashboard.get(householdId!);
      return res.data;
    },
    enabled: !!householdId,
    refetchInterval: 60_000,
  });

  // Lazy-fetch a full Routine (with steps) when the user taps a row in
  // the home-screen RoutinesWidget so we can hand it to RoutineStepper
  // without changing the dashboard payload shape.
  const handleOpenRoutine = async (routineId: string) => {
    const cached = queryClient.getQueryData<Routine>([
      "routine",
      routineId,
    ]);
    if (cached) {
      setOpenRoutine(cached);
      return;
    }
    const res = await routinesApi.getOne(routineId);
    queryClient.setQueryData(["routine", routineId], res.data);
    setOpenRoutine(res.data);
  };

  const showAgenda = modulesEnabled.calendar;
  const showSidebar =
    modulesEnabled.weather ||
    modulesEnabled.routines ||
    modulesEnabled.meals ||
    modulesEnabled.lists ||
    modulesEnabled.messages ||
    modulesEnabled.rewards;

  const hasAnyModule = showAgenda || showSidebar;

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <header className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">{getGreeting()}</h1>
          <p className="text-gray-500 dark:text-gray-400">
            {format(new Date(), "EEEE, MMMM d")}
          </p>
        </div>
        <NotificationBell />
      </header>

      {isError && (
        <div className="rounded-lg bg-red-50 dark:bg-red-900/30 p-4 text-red-700 dark:text-red-300 text-sm">
          Unable to load dashboard data. Please try again later.
        </div>
      )}

      {data?.vacation?.active && (
        <div className="flex items-start gap-3 rounded-xl border border-amber-300 bg-amber-50 p-4 text-amber-900 dark:border-amber-700 dark:bg-amber-900/20 dark:text-amber-200">
          <span className="text-2xl" aria-hidden>🏝</span>
          <div className="flex-1">
            <p className="font-semibold">
              Household on vacation
              {data.vacation.end_date
                ? ` until ${format(parseISO(data.vacation.end_date), "EEE, MMM d")}`
                : ""}
            </p>
            <p className="text-sm opacity-90">
              {data.vacation.reason
                ? data.vacation.reason
                : "Pausable routines are hidden. Routines marked “Pause on vacation = off” keep running."}
            </p>
          </div>
        </div>
      )}

      {data?.school_day?.reason && (
        <div className="flex items-start gap-3 rounded-xl border border-sky-300 bg-sky-50 p-4 text-sky-900 dark:border-sky-700 dark:bg-sky-900/20 dark:text-sky-200">
          <span className="text-2xl" aria-hidden>🎒</span>
          <div className="flex-1">
            <p className="font-semibold">
              No school today — {data.school_day.reason}
            </p>
            <p className="text-sm opacity-90">
              {(data.school_day.hidden_step_count ?? 0) > 0
                ? `${data.school_day.hidden_step_count} routine step${
                    data.school_day.hidden_step_count === 1 ? "" : "s"
                  } marked “Only on school days” are hidden.`
                : "Routine steps marked “Only on school days” are hidden."}
            </p>
          </div>
        </div>
      )}

      {!isLoading && !hasAnyModule && (
        <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-600 p-8 text-center">
          <p className="text-lg text-gray-400 dark:text-gray-500">
            All modules are turned off.
          </p>
          <p className="mt-1 text-sm text-gray-400 dark:text-gray-500">
            Go to ⚙️ Settings to enable modules like Calendar, Weather, Routines, and more.
          </p>
        </div>
      )}

      {/* Adaptive grid: 2/3+1/3 when both, full-width when only one */}
      {(isLoading || hasAnyModule) && (
        <div
          className={`grid gap-6 ${
            showAgenda && showSidebar
              ? "grid-cols-1 lg:grid-cols-3"
              : "grid-cols-1"
          }`}
        >
          {/* Agenda — takes 2 cols when sidebar present, full width otherwise */}
          {(isLoading || showAgenda) && (
            <div className={showAgenda && showSidebar ? "lg:col-span-2" : ""}>
              {isLoading ? (
                <div className="space-y-4">
                  <SkeletonLine className="h-6 w-40" />
                  {Array.from({ length: 4 }).map((_, i) => (
                    <SkeletonCard key={i} />
                  ))}
                </div>
              ) : (
                <AgendaSection buckets={data?.agenda ?? []} timeFormat={timeFormat} />
              )}
            </div>
          )}

          {/* Sidebar widgets — stacked in a column when agenda is present,
              or in a responsive grid when they have full width */}
          {(isLoading || showSidebar) && (
            <aside
              className={
                showAgenda
                  ? "space-y-6"
                  : "grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3"
              }
            >
              {isLoading ? (
                <>
                  <SkeletonCard />
                  <SkeletonCard />
                  <SkeletonCard />
                </>
              ) : (
                <>
                  {modulesEnabled.weather && <WeatherWidget />}
                  {modulesEnabled.routines && (
                    <RoutinesWidget
                      routines={data?.active_routines ?? []}
                      allDone={!!data?.routines_all_done}
                      onOpen={handleOpenRoutine}
                    />
                  )}
                  {modulesEnabled.meals && (
                    <MealsWidget meals={data?.today_meals ?? []} />
                  )}
                  {modulesEnabled.lists && (
                    <ListsWidget lists={data?.active_lists ?? []} />
                  )}
                  {modulesEnabled.messages && <MessagesWidget />}
                  {modulesEnabled.rewards && <LeaderboardWidget />}
                </>
              )}
            </aside>
          )}
        </div>
      )}

      {openRoutine && (
        <RoutineStepper
          routine={openRoutine}
          onClose={() => {
            setOpenRoutine(null);
            queryClient.invalidateQueries({ queryKey: ["dashboard"] });
            queryClient.invalidateQueries({ queryKey: ["routines-today"] });
          }}
        />
      )}
    </div>
  );
}
