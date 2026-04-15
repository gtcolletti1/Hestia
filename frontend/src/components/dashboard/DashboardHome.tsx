import { useQuery } from "@tanstack/react-query";
import { format, parseISO } from "date-fns";
import { dashboard } from "@/api/endpoints";
import { useHouseholdStore } from "@/stores/householdStore";
import WeatherWidget from "./WeatherWidget";
import type { DashboardData, AgendaBucket, MealPlan, Routine } from "@/types";

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

function AgendaSection({ buckets }: { buckets: AgendaBucket[] }) {
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
                      {format(parseISO(ev.start_time), "h:mm a")}
                      {" – "}
                      {format(parseISO(ev.end_time), "h:mm a")}
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

function RoutinesWidget({ routines }: { routines: Routine[] }) {
  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3">
      <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
        Active Routines
      </h3>
      {routines.length === 0 ? (
        <p className="text-sm text-gray-400 italic">No routines set up yet</p>
      ) : (
        <ul className="space-y-2">
          {routines.map((r) => (
            <li key={r.id} className="flex items-center gap-3 min-h-[44px]">
              <span className="text-xs font-semibold uppercase text-gray-400 w-16 shrink-0">
                {r.time_block}
              </span>
              <div className="min-w-0 flex-1">
                <p className="font-medium truncate">{r.name}</p>
                <p className="text-xs text-gray-400">
                  {r.steps.length} step{r.steps.length !== 1 ? "s" : ""}
                </p>
              </div>
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

  const { data, isLoading, isError } = useQuery<DashboardData>({
    queryKey: ["dashboard", householdId],
    queryFn: async () => {
      const res = await dashboard.get(householdId!);
      return res.data;
    },
    enabled: !!householdId,
    refetchInterval: 60_000,
  });

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <header>
        <h1 className="text-3xl font-bold">{getGreeting()}</h1>
        <p className="text-gray-500 dark:text-gray-400">
          {format(new Date(), "EEEE, MMMM d")}
        </p>
      </header>

      {isError && (
        <div className="rounded-lg bg-red-50 dark:bg-red-900/30 p-4 text-red-700 dark:text-red-300 text-sm">
          Unable to load dashboard data. Please try again later.
        </div>
      )}

      {/* Grid: Agenda 2/3 | Sidebar 1/3 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Agenda */}
        <div className="lg:col-span-2">
          {isLoading ? (
            <div className="space-y-4">
              <SkeletonLine className="h-6 w-40" />
              {Array.from({ length: 4 }).map((_, i) => (
                <SkeletonCard key={i} />
              ))}
            </div>
          ) : (
            <AgendaSection buckets={data?.agenda ?? []} />
          )}
        </div>

        {/* Sidebar */}
        <aside className="space-y-6">
          {isLoading ? (
            <>
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
            </>
          ) : (
            <>
              <WeatherWidget />
              <RoutinesWidget routines={data?.active_routines ?? []} />
              <MealsWidget meals={data?.today_meals ?? []} />
              <ListsWidget lists={data?.active_lists ?? []} />
            </>
          )}
        </aside>
      </div>
    </div>
  );
}
