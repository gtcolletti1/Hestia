import { useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { rewards as rewardsApi } from "@/api/endpoints";
import { useHouseholdStore } from "@/stores/householdStore";

interface Reward {
  id: string;
  title: string;
  description: string | null;
  points_cost: number;
  icon: string | null;
}

interface Props {
  reward: Reward | null;
  onClose: () => void;
  onSaved: () => void;
}

const REWARD_ICONS = ["🎁", "🍦", "🎮", "📱", "🎬", "🛒", "⏰", "🌟", "🏖️", "🎨", "📚", "🧸"];

export default function RewardForm({ reward, onClose, onSaved }: Props) {
  const householdId = useHouseholdStore((s) => s.householdId);
  const queryClient = useQueryClient();
  const isEditing = !!reward;

  const [title, setTitle] = useState(reward?.title ?? "");
  const [description, setDescription] = useState(reward?.description ?? "");
  const [pointsCost, setPointsCost] = useState(reward?.points_cost ?? 10);
  const [icon, setIcon] = useState(reward?.icon ?? "🎁");

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (isEditing) {
        return rewardsApi.update(reward.id, {
          title,
          description: description || undefined,
          points_cost: pointsCost,
          icon,
        });
      }
      return rewardsApi.create({
        title,
        description: description || undefined,
        points_cost: pointsCost,
        icon,
        household_id: householdId!,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rewards"] });
      onSaved();
    },
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    saveMutation.mutate();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md rounded-2xl bg-white dark:bg-gray-800 p-6 shadow-2xl space-y-5 mx-4"
      >
        <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">
          {isEditing ? "Edit Reward" : "New Reward"}
        </h2>

        {/* Icon picker */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Icon
          </label>
          <div className="flex flex-wrap gap-2">
            {REWARD_ICONS.map((emoji) => (
              <button
                key={emoji}
                type="button"
                onClick={() => setIcon(emoji)}
                className={`flex h-10 w-10 items-center justify-center rounded-lg text-xl transition ${
                  icon === emoji
                    ? "bg-blue-100 dark:bg-blue-900/40 ring-2 ring-blue-500 scale-110"
                    : "bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600"
                }`}
              >
                {emoji}
              </button>
            ))}
          </div>
        </div>

        {/* Title */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Title
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Extra Screen Time"
            required
            className="w-full rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-base focus:ring-2 focus:ring-blue-200 dark:focus:ring-blue-800"
          />
        </div>

        {/* Description */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Description <span className="text-gray-400">(optional)</span>
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What does this reward include?"
            rows={2}
            className="w-full rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-base resize-none"
          />
        </div>

        {/* Points cost */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Points Cost
          </label>
          <input
            type="number"
            min={1}
            value={pointsCost}
            onChange={(e) => setPointsCost(parseInt(e.target.value) || 1)}
            className="w-32 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-base tabular-nums"
          />
        </div>

        {/* Actions */}
        <div className="flex gap-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 rounded-xl border border-gray-300 dark:border-gray-600 py-3 font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 min-h-[48px]"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={saveMutation.isPending || !title.trim()}
            className="flex-1 rounded-xl bg-blue-600 py-3 font-semibold text-white shadow hover:bg-blue-700 disabled:opacity-50 min-h-[48px]"
          >
            {saveMutation.isPending ? "Saving…" : isEditing ? "Update" : "Create"}
          </button>
        </div>

        {saveMutation.isError && (
          <p className="text-center text-sm text-red-600 dark:text-red-400">
            Failed to save. Please try again.
          </p>
        )}
      </form>
    </div>
  );
}
