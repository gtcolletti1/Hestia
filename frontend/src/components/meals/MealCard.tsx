import type { MealPlan, Profile } from "@/types";

const MEAL_EMOJI: Record<MealPlan["meal_type"], string> = {
  breakfast: "🌅",
  lunch: "☀️",
  dinner: "🌙",
  snack: "🍿",
};

const MEAL_LABEL: Record<MealPlan["meal_type"], string> = {
  breakfast: "Breakfast",
  lunch: "Lunch",
  dinner: "Dinner",
  snack: "Snack",
};

interface MealCardProps {
  meal: MealPlan;
  profiles: Profile[];
  onEdit?: (meal: MealPlan) => void;
}

export default function MealCard({ meal, profiles, onEdit }: MealCardProps) {
  const cook = profiles.find((p) => p.id === meal.assigned_profile_id);

  return (
    <div
      onClick={() => onEdit?.(meal)}
      className="w-full text-left rounded-xl bg-white dark:bg-gray-800 shadow-sm border border-gray-200 dark:border-gray-700 p-4 hover:shadow-md transition-shadow cursor-pointer"
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") onEdit?.(meal);
      }}
    >
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 leading-tight">
          {meal.title}
        </h3>
        <span className="shrink-0 rounded-full bg-gray-100 dark:bg-gray-700 px-2 py-0.5 text-sm">
          {MEAL_EMOJI[meal.meal_type]} {MEAL_LABEL[meal.meal_type]}
        </span>
      </div>

      {meal.description && (
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400 line-clamp-2">
          {meal.description}
        </p>
      )}

      {meal.recipe_url && (
        <a
          href={meal.recipe_url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="mt-2 inline-flex items-center gap-1 text-sm text-blue-600 dark:text-blue-400 hover:underline"
        >
          📖 Recipe
        </a>
      )}

      {cook && (
        <div className="mt-2 flex items-center gap-2">
          <span
            className="inline-block h-3 w-3 rounded-full"
            style={{ backgroundColor: cook.color }}
          />
          <span className="text-sm text-gray-600 dark:text-gray-300">
            {cook.name}
          </span>
        </div>
      )}
    </div>
  );
}
