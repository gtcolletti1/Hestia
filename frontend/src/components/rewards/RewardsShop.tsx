import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { rewards as rewardsApi } from "@/api/endpoints";
import { useHouseholdStore } from "@/stores/householdStore";
import { useAuthStore } from "@/stores/authStore";
import RewardCard from "./RewardCard";
import RewardForm from "./RewardForm";

interface Reward {
  id: string;
  title: string;
  description: string | null;
  points_cost: number;
  icon: string | null;
  is_active: number;
}

interface LeaderboardEntry {
  profile_id: string;
  display_name: string;
  avatar_url: string | null;
  total_points: number;
}

export default function RewardsShop() {
  const householdId = useHouseholdStore((s) => s.householdId);
  const profile = useAuthStore((s) => s.profile);
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editingReward, setEditingReward] = useState<Reward | null>(null);
  const [redeemingId, setRedeemingId] = useState<string | null>(null);
  const [redeemSuccess, setRedeemSuccess] = useState<string | null>(null);
  const [redeemError, setRedeemError] = useState<string | null>(null);

  const isAdmin = profile?.role === "admin";

  const { data: rewardsList = [] } = useQuery<Reward[]>({
    queryKey: ["rewards", householdId],
    queryFn: async () => (await rewardsApi.getAll(householdId!)).data,
    enabled: !!householdId,
  });

  const { data: leaderboard = [] } = useQuery<LeaderboardEntry[]>({
    queryKey: ["leaderboard", householdId],
    queryFn: async () => (await rewardsApi.getLeaderboard(householdId!)).data,
    enabled: !!householdId,
  });

  const myPoints =
    leaderboard.find((e) => e.profile_id === profile?.id)?.total_points ?? 0;

  const redeemMutation = useMutation({
    mutationFn: (rewardId: string) =>
      rewardsApi.redeem({
        reward_id: rewardId,
        profile_id: profile!.id,
        household_id: householdId!,
      }),
    onSuccess: (_data, rewardId) => {
      const reward = rewardsList.find((r) => r.id === rewardId);
      setRedeemSuccess(`🎉 Redeemed "${reward?.title}"!`);
      setTimeout(() => setRedeemSuccess(null), 3000);
      setRedeemError(null);
      queryClient.invalidateQueries({ queryKey: ["leaderboard"] });
      queryClient.invalidateQueries({ queryKey: ["rewards"] });
    },
    onError: (err: unknown) => {
      const msg =
        err instanceof Error ? err.message : "Not enough points";
      setRedeemError(msg);
      setTimeout(() => setRedeemError(null), 3000);
    },
    onSettled: () => setRedeemingId(null),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => rewardsApi.delete(id),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["rewards"] }),
  });

  const handleRedeem = (rewardId: string) => {
    setRedeemingId(rewardId);
    setRedeemError(null);
    redeemMutation.mutate(rewardId);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            🏆 Rewards Shop
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Earn points by completing routines, spend them on rewards!
          </p>
        </div>
        {isAdmin && (
          <button
            onClick={() => {
              setEditingReward(null);
              setShowForm(true);
            }}
            className="rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow hover:bg-blue-700 active:scale-95 transition min-h-[44px]"
          >
            + Add Reward
          </button>
        )}
      </div>

      {/* Points balance banner */}
      <div className="rounded-2xl bg-gradient-to-r from-amber-400 to-orange-500 p-6 text-white shadow-lg">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium opacity-90">Your Points</p>
            <p className="text-4xl font-bold tabular-nums">{myPoints} ⭐</p>
          </div>
          <div className="text-6xl opacity-80">🎯</div>
        </div>
      </div>

      {/* Success / error toasts */}
      {redeemSuccess && (
        <div className="rounded-xl bg-green-100 dark:bg-green-900/30 border border-green-300 dark:border-green-700 p-4 text-green-800 dark:text-green-300 text-sm font-medium animate-pulse">
          {redeemSuccess}
        </div>
      )}
      {redeemError && (
        <div className="rounded-xl bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-700 p-4 text-red-800 dark:text-red-300 text-sm font-medium">
          ❌ {redeemError}
        </div>
      )}

      {/* Rewards grid */}
      {rewardsList.length === 0 ? (
        <div className="rounded-2xl border-2 border-dashed border-gray-300 dark:border-gray-600 p-12 text-center">
          <span className="text-5xl">🎁</span>
          <p className="mt-3 text-gray-500 dark:text-gray-400 font-medium">
            No rewards yet
          </p>
          {isAdmin && (
            <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
              Add rewards for family members to redeem!
            </p>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {rewardsList.map((reward) => (
            <RewardCard
              key={reward.id}
              reward={reward}
              myPoints={myPoints}
              isRedeeming={redeemingId === reward.id}
              isAdmin={isAdmin}
              onRedeem={() => handleRedeem(reward.id)}
              onEdit={() => {
                setEditingReward(reward);
                setShowForm(true);
              }}
              onDelete={() => deleteMutation.mutate(reward.id)}
            />
          ))}
        </div>
      )}

      {/* Leaderboard */}
      <div className="rounded-2xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          🏅 Leaderboard
        </h2>
        <div className="space-y-3">
          {leaderboard.map((entry, i) => {
            const medals = ["🥇", "🥈", "🥉"];
            return (
              <div
                key={entry.profile_id}
                className={`flex items-center gap-3 rounded-xl p-3 ${
                  entry.profile_id === profile?.id
                    ? "bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700"
                    : "bg-gray-50 dark:bg-gray-700/50"
                }`}
              >
                <span className="text-xl w-8 text-center">
                  {medals[i] ?? `#${i + 1}`}
                </span>
                <span className="flex-1 font-medium text-gray-900 dark:text-gray-100">
                  {entry.display_name}
                </span>
                <span className="font-bold text-amber-600 dark:text-amber-400 tabular-nums">
                  {entry.total_points} ⭐
                </span>
              </div>
            );
          })}
          {leaderboard.length === 0 && (
            <p className="text-sm text-gray-400 italic">
              Complete routine steps to earn points!
            </p>
          )}
        </div>
      </div>

      {/* Reward form modal */}
      {showForm && (
        <RewardForm
          reward={editingReward}
          onClose={() => setShowForm(false)}
          onSaved={() => setShowForm(false)}
        />
      )}
    </div>
  );
}
