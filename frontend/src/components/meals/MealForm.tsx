import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { meals } from "@/api/endpoints";
import { useHouseholdStore } from "@/stores/householdStore";
import type { MealPlan, Profile } from "@/types";

const MEAL_TYPES: {
  value: MealPlan["meal_type"];
  emoji: string;
  label: string;
}[] = [
  { value: "breakfast", emoji: "🌅", label: "Breakfast" },
  { value: "lunch", emoji: "☀️", label: "Lunch" },
  { value: "dinner", emoji: "🌙", label: "Dinner" },
  { value: "snack", emoji: "🍿", label: "Snack" },
];

interface MealFormProps {
  meal?: MealPlan;
  initialDate?: string;
  initialType?: MealPlan["meal_type"];
  profiles: Profile[];
  onClose: () => void;
  onSaved: () => void;
}

export default function MealForm({
  meal,
  initialDate,
  initialType,
  profiles,
  onClose,
  onSaved,
}: MealFormProps) {
  const householdId = useHouseholdStore((s) => s.householdId)!;
  const queryClient = useQueryClient();
  const isEditing = !!meal;

  const [date, setDate] = useState(
    meal?.date || initialDate || format(new Date(), "yyyy-MM-dd"),
  );
  const [mealType, setMealType] = useState<MealPlan["meal_type"]>(
    meal?.meal_type || initialType || "dinner",
  );
  const [title, setTitle] = useState(meal?.title || "");
  const [description, setDescription] = useState(meal?.description || "");
  const [recipeUrl, setRecipeUrl] = useState(meal?.recipe_url || "");
  const [assignedProfileId, setAssignedProfileId] = useState(
    meal?.assigned_profile_id || "",
  );

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["meals"] });
    onSaved();
  };

  const createMutation = useMutation({
    mutationFn: (data: Partial<MealPlan>) => meals.create(householdId, data),
    onSuccess: invalidate,
  });

  const updateMutation = useMutation({
    mutationFn: (data: Partial<MealPlan>) =>
      meals.update(householdId, meal!.id, data),
    onSuccess: invalidate,
  });

  const deleteMutation = useMutation({
    mutationFn: () => meals.delete(householdId, meal!.id),
    onSuccess: invalidate,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const data: Partial<MealPlan> = {
      date,
      meal_type: mealType,
      title: title.trim(),
      description: description.trim() || undefined,
      recipe_url: recipeUrl.trim() || undefined,
      assigned_profile_id: assignedProfileId || undefined,
    };

    if (isEditing) {
      updateMutation.mutate(data);
    } else {
      createMutation.mutate(data);
    }
  };

  const isPending =
    createMutation.isPending ||
    updateMutation.isPending ||
    deleteMutation.isPending;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-lg rounded-2xl bg-white dark:bg-gray-800 shadow-xl max-h-[90vh] overflow-y-auto">
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
            {isEditing ? "Edit Meal" : "Add Meal"}
          </h2>

          {/* Date picker */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Date
            </label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-3 text-base text-gray-900 dark:text-gray-100 min-h-[44px]"
              required
            />
          </div>

          {/* Meal type toggle */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Meal Type
            </label>
            <div className="grid grid-cols-4 gap-2">
              {MEAL_TYPES.map((mt) => (
                <button
                  key={mt.value}
                  type="button"
                  onClick={() => setMealType(mt.value)}
                  className={`flex flex-col items-center gap-1 rounded-xl py-3 px-2 text-sm font-medium transition-colors min-h-[44px] ${
                    mealType === mt.value
                      ? "bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 ring-2 ring-blue-500"
                      : "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600"
                  }`}
                >
                  <span className="text-xl">{mt.emoji}</span>
                  <span>{mt.label}</span>
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
              placeholder="What's cooking?"
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-3 text-base text-gray-900 dark:text-gray-100 min-h-[44px]"
              required
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Notes, ingredients, etc."
              rows={3}
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-3 text-base text-gray-900 dark:text-gray-100"
            />
          </div>

          {/* Recipe URL */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Recipe URL
            </label>
            <input
              type="url"
              value={recipeUrl}
              onChange={(e) => setRecipeUrl(e.target.value)}
              placeholder="https://..."
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-3 text-base text-gray-900 dark:text-gray-100 min-h-[44px]"
            />
          </div>

          {/* Who's cooking */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Who&apos;s cooking?
            </label>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setAssignedProfileId("")}
                className={`rounded-full px-4 py-2 text-sm font-medium min-h-[44px] transition-colors ${
                  !assignedProfileId
                    ? "bg-gray-800 dark:bg-gray-200 text-white dark:text-gray-900"
                    : "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400"
                }`}
              >
                Anyone
              </button>
              {profiles.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => setAssignedProfileId(p.id)}
                  className={`flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium min-h-[44px] transition-colors ${
                    assignedProfileId === p.id
                      ? "ring-2 ring-blue-500 bg-blue-50 dark:bg-blue-900/50 text-gray-900 dark:text-gray-100"
                      : "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300"
                  }`}
                >
                  <span
                    className="h-4 w-4 rounded-full"
                    style={{ backgroundColor: p.color }}
                  />
                  {p.name}
                </button>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-3 pt-2">
            <button
              type="submit"
              disabled={isPending || !title.trim()}
              className="flex-1 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-4 min-h-[44px] disabled:opacity-50 transition-colors"
            >
              {isPending ? "Saving..." : "Save"}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-xl bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 font-semibold py-3 px-4 min-h-[44px] transition-colors"
            >
              Cancel
            </button>
          </div>

          {isEditing && (
            <button
              type="button"
              onClick={() => deleteMutation.mutate()}
              disabled={isPending}
              className="w-full rounded-xl bg-red-100 dark:bg-red-900/30 hover:bg-red-200 dark:hover:bg-red-900/50 text-red-600 dark:text-red-400 font-semibold py-3 px-4 min-h-[44px] disabled:opacity-50 transition-colors"
            >
              Delete Meal
            </button>
          )}
        </form>
      </div>
    </div>
  );
}
