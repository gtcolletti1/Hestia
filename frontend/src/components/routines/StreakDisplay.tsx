import { useQuery } from "@tanstack/react-query";
import { routines as routinesApi } from "@/api/endpoints";

interface Props {
  routineId: string;
  profileId: string;
}

export default function StreakDisplay({ routineId, profileId }: Props) {
  const { data, isLoading } = useQuery({
    queryKey: ["routine-streak", routineId, profileId],
    queryFn: async () => (await routinesApi.getStreak(routineId, profileId)).data,
    enabled: !!profileId,
  });

  if (isLoading) {
    return (
      <div className="flex justify-center py-4">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
      </div>
    );
  }

  if (!data) return null;

  const streak = data.current_streak;

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
      <div className="flex items-center gap-2">
        <span className="text-2xl">🔥</span>
        <span className="text-lg font-bold">
          {streak} day{streak !== 1 ? "s" : ""} in a row!
        </span>
      </div>
    </div>
  );
}
