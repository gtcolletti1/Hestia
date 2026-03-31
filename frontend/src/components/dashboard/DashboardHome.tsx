import { useQuery } from "@tanstack/react-query";
import {
  format,
  parseISO,
  getHours,
  isToday,
  compareAsc,
} from "date-fns";
import client from "@/api/client";

// ── Local types (used if src/types/index.ts does not exist yet) ──

interface CalendarEvent {
  id: string;
  title: string;
  start: string;
  end: string;
  location?: string;
  profile_id: string;
  profile_name: string;
  profile_color: string;
}

interface RoutineStep {
  id: string;
  title: string;
  done: boolean;
}

interface ActiveRoutine {
  id: string;
  title: string;
  steps: RoutineStep[];
  profile_name: string;
  profile_color: string;
}

interface Meal {
  id: string;
  type: "breakfast" | "lunch" | "dinner" | "snack";
  title: string;
  description?: string;
}

interface ListSummary {
  id: string;
  title: string;
  total: number;
  checked: number;
}

interface DashboardData {
  events: CalendarEvent[];
  active_routine: ActiveRoutine | null;
  meals: Meal[];
  lists: ListSummary[];
}

// ── Helpers ──

function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

type TimeBucket = "Morning" | "Afternoon" | "Evening";

function getBucket(iso: string): TimeBucket {
  const h = getHours(parseISO(iso));
  if (h < 12) return "Morning";
  if (h < 17) return "Afternoon";
  return "Evening";
}

const BUCKET_ORDER: TimeBucket[] = ["Morning", "Afternoon", "Evening"];

function groupByBucket(events: CalendarEvent[]): Record<TimeBucket, CalendarEvent[]> {
  const groups: Record<TimeBucket, CalendarEvent[]> = {
    Morning: [],
    Afternoon: [],
    Evening: [],
  };
  for (const ev of events) {
    groups[getBucket(ev.start)].push(ev);
  }
  for (const key of BUCKET_ORDER) {
    groups[key].sort((a, b) => compareAsc(parseISO(a.start), parseISO(b.start)));
  }
  return groups;
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

function AgendaSection({ events }: { events: CalendarEvent[] }) {
  const groups = groupByBucket(events);

  return (
    <section className="space-y-6">
      <h2 className="text-lg font-semibold">Today&apos;s Agenda</h2>

      {BUCKET_ORDER.map((bucket) => (
        <div key={bucket}>
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">
            {bucket}
          </h3>

          {groups[bucket].length === 0 ? (
            <p className="text-sm text-gray-400 dark:text-gray-500 italic">
              No events
            </p>
          ) : (
            <ul className="space-y-2">
              {groups[bucket].map((ev) => (
                <li
                  key={ev.id}
                  className="flex items-start gap-3 rounded-lg bg-white dark:bg-gray-800 p-3 shadow-sm min-h-[44px]"
                >
                  <span
                    className="mt-1.5 h-3 w-3 shrink-0 rounded-full"
                    style={{ backgroundColor: ev.profile_color }}
                  />
                  <div className="min-w-0 flex-1">
                    <p className="font-medium truncate">{ev.title}</p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {format(parseISO(ev.start), "h:mm a")}
                      {" – "}
                      {format(parseISO(ev.end), "h:mm a")}
                    </p>
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

function RoutineWidget({ routine }: { routine: ActiveRoutine }) {
  const done = routine.steps.filter((s) => s.done).length;
  const total = routine.steps.length;
  const pct = total === 0 ? 0 : Math.round((done / total) * 100);

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 p-4">
      <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
        Active Routine
      </h3>
      <div className="flex items-center gap-2 mb-2">
        <span
          className="h-3 w-3 rounded-full shrink-0"
          style={{ backgroundColor: routine.profile_color }}
        />
        <p className="font-semibold truncate">{routine.title}</p>
      </div>
      <div className="w-full rounded-full bg-gray-200 dark:bg-gray-700 h-2 mb-1">
        <div
          className="h-2 rounded-full bg-blue-500 transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="text-xs text-gray-500 dark:text-gray-400">
        {done}/{total} steps done
      </p>
    </div>
  );
}

function MealsWidget({ meals }: { meals: Meal[] }) {
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
            <li
              key={m.id}
              className="flex items-center gap-3 min-h-[44px]"
            >
              <span className="text-xs font-semibold uppercase text-gray-400 w-16 shrink-0">
                {MEAL_LABELS[m.type] ?? m.type}
              </span>
              <span className="truncate">{m.title}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ListsWidget({ lists }: { lists: ListSummary[] }) {
  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3">
      <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
        Lists
      </h3>
      {lists.length === 0 ? (
        <p className="text-sm text-gray-400 italic">No active lists</p>
      ) : (
        <ul className="space-y-3">
          {lists.map((l) => {
            const pct = l.total === 0 ? 0 : Math.round((l.checked / l.total) * 100);
            return (
              <li key={l.id}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium truncate">{l.title}</span>
                  <span className="text-xs text-gray-400 shrink-0 ml-2">
                    {l.checked}/{l.total}
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
  const householdId = localStorage.getItem("household_id") ?? "default";

  const { data, isLoading, isError } = useQuery<DashboardData>({
    queryKey: ["dashboard", householdId],
    queryFn: async () => {
      const res = await client.get<DashboardData>("/dashboard", {
        params: { household_id: householdId },
      });
      return res.data;
    },
    refetchInterval: 60_000,
  });

  const todayEvents = (data?.events ?? []).filter((e) =>
    isToday(parseISO(e.start)),
  );

  return (
    <div className="space-y-6">
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
            <AgendaSection events={todayEvents} />
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
              {data?.active_routine && (
                <RoutineWidget routine={data.active_routine} />
              )}
              <MealsWidget meals={data?.meals ?? []} />
              <ListsWidget lists={data?.lists ?? []} />
            </>
          )}
        </aside>
      </div>
    </div>
  );
}
