import { useQuery } from "@tanstack/react-query";
import { format, subDays, isSameDay, startOfDay } from "date-fns";
import client from "@/api/client";

interface StreakData {
  current_streak: number;
  total_completions: number;
  completed_dates: string[]; // ISO date strings
}

interface Props {
  routineId: string;
}

export default function StreakDisplay({ routineId }: Props) {
  const { data, isLoading } = useQuery<StreakData>({
    queryKey: ["routine-streak", routineId],
    queryFn: async () => (await client.get(`/routines/${routineId}/streak`)).data,
  });

  if (isLoading) {
    return (
      <div className="flex justify-center py-4">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
      </div>
    );
  }

  if (!data) return null;

  const today = startOfDay(new Date());
  const completedSet = new Set(
    data.completed_dates.map((d) => startOfDay(new Date(d)).toISOString()),
  );

  const last30 = Array.from({ length: 30 }, (_, i) => {
    const date = subDays(today, 29 - i);
    return {
      date,
      isToday: isSameDay(date, today),
      completed: completedSet.has(startOfDay(date).toISOString()),
    };
  });

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
      {/* Current streak */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-2xl">🔥</span>
          <span className="text-lg font-bold">
            {data.current_streak} day{data.current_streak !== 1 ? "s" : ""} in a row!
          </span>
        </div>
        <span className="text-sm text-gray-500 dark:text-gray-400">
          {data.total_completions} total
        </span>
      </div>

      {/* Dot grid — last 30 days */}
      <div className="grid grid-cols-10 gap-2">
        {last30.map(({ date, isToday, completed }) => (
          <div
            key={date.toISOString()}
            title={format(date, "MMM d")}
            className={`flex h-6 w-6 items-center justify-center rounded-full text-[9px] font-medium transition ${
              isToday
                ? completed
                  ? "ring-2 ring-blue-500 bg-green-500 text-white"
                  : "ring-2 ring-blue-500 bg-gray-200 text-gray-600 dark:bg-gray-600 dark:text-gray-300"
                : completed
                  ? "bg-green-500 text-white"
                  : "bg-gray-200 text-gray-400 dark:bg-gray-700 dark:text-gray-500"
            }`}
          >
            {isToday ? "T" : ""}
          </div>
        ))}
      </div>

      <p className="mt-2 text-center text-xs text-gray-400 dark:text-gray-500">Last 30 days</p>
    </div>
  );
}
