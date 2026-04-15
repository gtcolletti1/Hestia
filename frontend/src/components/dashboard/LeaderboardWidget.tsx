import { useQuery } from "@tanstack/react-query";
import { rewards } from "@/api/endpoints";
import { useHouseholdStore } from "@/stores/householdStore";

interface LeaderboardEntry {
  profile_id: string;
  display_name: string;
  avatar_url: string | null;
  total_points: number;
}

export default function LeaderboardWidget() {
  const householdId = useHouseholdStore((s) => s.householdId);

  const { data: entries = [] } = useQuery<LeaderboardEntry[]>({
    queryKey: ["leaderboard", householdId],
    queryFn: () => rewards.getLeaderboard(householdId!).then((r) => r.data),
    enabled: !!householdId,
    staleTime: 2 * 60 * 1000,
  });

  // Only show if someone has points
  const hasPoints = entries.some((e) => e.total_points > 0);
  if (!hasPoints) return null;

  return (
    <section className="rounded-2xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-4">
      <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">
        🏆 Points Leaderboard
      </h3>
      <div className="space-y-2">
        {entries.map((entry, i) => (
          <div
            key={entry.profile_id}
            className="flex items-center gap-3 text-sm"
          >
            <span className="w-5 text-center font-bold text-gray-400">
              {i === 0 ? "🥇" : i === 1 ? "🥈" : i === 2 ? "🥉" : `${i + 1}`}
            </span>
            {entry.avatar_url ? (
              <img src={entry.avatar_url} alt="" className="w-6 h-6 rounded-full" />
            ) : (
              <span className="text-lg">👤</span>
            )}
            <span className="flex-1 font-medium text-gray-900 dark:text-gray-100 truncate">
              {entry.display_name}
            </span>
            <span className="font-semibold text-amber-600 dark:text-amber-400 tabular-nums">
              {entry.total_points} ⭐
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
