import React from "react";

/* -------------------------------------------------------------------------- */
/*  Types                                                                     */
/* -------------------------------------------------------------------------- */

interface RoutineCompletion {
  name: string;
  completed: number;
  total: number;
}

interface HeatmapCell {
  /** 0 = Sunday … 6 = Saturday */
  day: number;
  /** 0–23 */
  hour: number;
  count: number;
}

interface ActivityItem {
  id: string;
  action: string;
  detail: string;
  timestamp: string;
}

interface WeeklyStats {
  totalEvents: number;
  routinesCompleted: number;
  listItemsChecked: number;
}

interface AnalyticsWidgetsProps {
  routines: RoutineCompletion[];
  heatmap: HeatmapCell[];
  activities: ActivityItem[];
  stats: WeeklyStats;
}

/* -------------------------------------------------------------------------- */
/*  Sub-components                                                            */
/* -------------------------------------------------------------------------- */

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function BarChart({ routines }: { routines: RoutineCompletion[] }) {
  const maxTotal = Math.max(...routines.map((r) => r.total), 1);

  return (
    <div className="space-y-3">
      <h3 className="text-lg font-semibold">Routine Completion Rate</h3>
      {routines.map((r) => {
        const pct = r.total > 0 ? Math.round((r.completed / r.total) * 100) : 0;
        return (
          <div key={r.name}>
            <div className="flex justify-between text-sm mb-1">
              <span>{r.name}</span>
              <span className="tabular-nums">
                {r.completed}/{r.total} ({pct}%)
              </span>
            </div>
            <div className="h-4 rounded bg-gray-200 dark:bg-gray-700 overflow-hidden">
              <div
                className="h-full rounded transition-all"
                style={{
                  width: `${(r.completed / maxTotal) * 100}%`,
                  backgroundColor: "var(--accent-color, #3b82f6)",
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function intensityClass(count: number, max: number): string {
  if (count === 0) return "bg-gray-100 dark:bg-gray-800";
  const ratio = count / max;
  if (ratio < 0.25) return "bg-blue-200 dark:bg-blue-900";
  if (ratio < 0.5) return "bg-blue-400 dark:bg-blue-700";
  if (ratio < 0.75) return "bg-blue-500 dark:bg-blue-500";
  return "bg-blue-700 dark:bg-blue-300";
}

function BusyTimesHeatmap({ heatmap }: { heatmap: HeatmapCell[] }) {
  const maxCount = Math.max(...heatmap.map((c) => c.count), 1);

  // Build a lookup: key = "day-hour"
  const lookup = new Map<string, number>();
  heatmap.forEach((c) => lookup.set(`${c.day}-${c.hour}`, c.count));

  const hours = Array.from({ length: 24 }, (_, i) => i);

  return (
    <div>
      <h3 className="text-lg font-semibold mb-2">Busy Times</h3>
      <div className="overflow-x-auto">
        <table className="border-collapse text-xs">
          <thead>
            <tr>
              <th className="pr-2" />
              {hours.map((h) => (
                <th key={h} className="px-0.5 font-normal text-gray-500">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {DAYS.map((dayName, dayIdx) => (
              <tr key={dayName}>
                <td className="pr-2 font-medium text-right">{dayName}</td>
                {hours.map((h) => {
                  const count = lookup.get(`${dayIdx}-${h}`) ?? 0;
                  return (
                    <td key={h} className="p-0">
                      <div
                        className={`w-4 h-4 rounded-sm ${intensityClass(count, maxCount)}`}
                        title={`${dayName} ${h}:00 — ${count} event(s)`}
                      />
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ActivityFeed({ activities }: { activities: ActivityItem[] }) {
  return (
    <div>
      <h3 className="text-lg font-semibold mb-2">Recent Activity</h3>
      {activities.length === 0 ? (
        <p className="text-sm text-gray-500">No recent activity.</p>
      ) : (
        <ul className="divide-y divide-gray-200 dark:divide-gray-700">
          {activities.map((a) => (
            <li key={a.id} className="py-2 flex justify-between text-sm">
              <div>
                <span className="font-medium">{a.action}</span>{" "}
                <span className="text-gray-500">{a.detail}</span>
              </div>
              <time className="text-gray-400 whitespace-nowrap ml-4">
                {new Date(a.timestamp).toLocaleString()}
              </time>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function StatsCards({ stats }: { stats: WeeklyStats }) {
  const cards = [
    { label: "Events This Week", value: stats.totalEvents, emoji: "📅" },
    { label: "Routines Completed", value: stats.routinesCompleted, emoji: "✅" },
    { label: "List Items Checked", value: stats.listItemsChecked, emoji: "☑️" },
  ];

  return (
    <div className="grid grid-cols-3 gap-4">
      {cards.map((c) => (
        <div
          key={c.label}
          className="rounded-lg border border-gray-200 dark:border-gray-700 p-4 text-center"
        >
          <div className="text-2xl mb-1">{c.emoji}</div>
          <div className="text-2xl font-bold tabular-nums">{c.value}</div>
          <div className="text-xs text-gray-500 mt-1">{c.label}</div>
        </div>
      ))}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/*  Main component                                                            */
/* -------------------------------------------------------------------------- */

export default function AnalyticsWidgets({
  routines,
  heatmap,
  activities,
  stats,
}: AnalyticsWidgetsProps) {
  return (
    <section className="space-y-8">
      <h2 className="text-xl font-bold">Analytics</h2>
      <StatsCards stats={stats} />
      <BarChart routines={routines} />
      <BusyTimesHeatmap heatmap={heatmap} />
      <ActivityFeed activities={activities} />
    </section>
  );
}
