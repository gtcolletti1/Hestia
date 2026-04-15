interface Reward {
  id: string;
  title: string;
  description: string | null;
  points_cost: number;
  icon: string | null;
}

interface Props {
  reward: Reward;
  myPoints: number;
  isRedeeming: boolean;
  isAdmin: boolean;
  onRedeem: () => void;
  onEdit: () => void;
  onDelete: () => void;
}

export default function RewardCard({
  reward,
  myPoints,
  isRedeeming,
  isAdmin,
  onRedeem,
  onEdit,
  onDelete,
}: Props) {
  const canAfford = myPoints >= reward.points_cost;

  return (
    <div className="relative flex flex-col rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5 shadow-sm hover:shadow-md transition-shadow">
      {/* Admin actions */}
      {isAdmin && (
        <div className="absolute top-3 right-3 flex gap-1">
          <button
            onClick={onEdit}
            className="rounded-lg p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/30 transition"
            aria-label="Edit reward"
          >
            ✏️
          </button>
          <button
            onClick={onDelete}
            className="rounded-lg p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 transition"
            aria-label="Delete reward"
          >
            🗑️
          </button>
        </div>
      )}

      {/* Icon */}
      <div className="text-4xl mb-3">{reward.icon ?? "🎁"}</div>

      {/* Title & description */}
      <h3 className="text-base font-bold text-gray-900 dark:text-gray-100">
        {reward.title}
      </h3>
      {reward.description && (
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">
          {reward.description}
        </p>
      )}

      {/* Cost & redeem */}
      <div className="mt-auto pt-4 flex items-center justify-between">
        <span className="text-lg font-bold text-amber-600 dark:text-amber-400 tabular-nums">
          {reward.points_cost} ⭐
        </span>
        <button
          onClick={onRedeem}
          disabled={!canAfford || isRedeeming}
          className={`rounded-xl px-4 py-2 text-sm font-semibold transition active:scale-95 min-h-[40px] ${
            canAfford
              ? "bg-green-600 text-white hover:bg-green-700 shadow"
              : "bg-gray-200 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed"
          }`}
        >
          {isRedeeming ? "..." : canAfford ? "Redeem" : "Need more ⭐"}
        </button>
      </div>
    </div>
  );
}
