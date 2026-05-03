import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import { meals } from "@/api/endpoints";
import { useHouseholdStore } from "@/stores/householdStore";
import type { MealPlan } from "@/types";

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

const MEAL_ORDER: MealPlan["meal_type"][] = [
  "breakfast",
  "lunch",
  "dinner",
  "snack",
];

const MEAL_HOUR_START: Record<MealPlan["meal_type"], number> = {
  breakfast: 6,
  lunch: 11,
  dinner: 17,
  snack: 20,
};

function getNextMealType(): MealPlan["meal_type"] {
  const hour = new Date().getHours();
  if (hour < MEAL_HOUR_START.lunch) return "breakfast";
  if (hour < MEAL_HOUR_START.dinner) return "lunch";
  if (hour < MEAL_HOUR_START.snack) return "dinner";
  return "snack";
}

export default function TodaysMeals() {
  const householdId = useHouseholdStore((s) => s.householdId);
  const today = format(new Date(), "yyyy-MM-dd");
  const nextMealType = getNextMealType();

  const { data: todayMeals = [] } = useQuery({
    queryKey: ["meals", "today", householdId, today],
    queryFn: () =>
      meals.getAll(householdId!, { date: today }).then((r) => r.data),
    enabled: !!householdId,
  });

  const sortedMeals = [...todayMeals].sort(
    (a, b) =>
      MEAL_ORDER.indexOf(a.meal_type) - MEAL_ORDER.indexOf(b.meal_type),
  );

  if (sortedMeals.length === 0) {
    return (
      <div className="rounded-2xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-6 text-center">
        <p className="text-2xl mb-2">🍽️</p>
        <p className="text-gray-500 dark:text-gray-400 text-lg">
          No meals planned for today
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100">
        🍽️ Today&apos;s Meals
      </h3>
      <div className="space-y-2">
        {sortedMeals.map((meal) => {
          const isNext = meal.meal_type === nextMealType;
          return (
            <div
              key={meal.id}
              className={`rounded-xl border p-4 transition-colors ${
                isNext
                  ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20 ring-2 ring-blue-400/30"
                  : "border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
              }`}
            >
              <div className="flex items-center gap-3">
                <span className="text-2xl">{MEAL_EMOJI[meal.meal_type]}</span>
                <div className="min-w-0 flex-1">
                  <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                    {MEAL_LABEL[meal.meal_type]}
                    {isNext && (
                      <span className="ml-2 text-blue-600 dark:text-blue-400 normal-case">
                        — Up Next
                      </span>
                    )}
                  </div>
                  <div className="text-xl font-bold text-gray-900 dark:text-gray-100 truncate">
                    {meal.title}
                  </div>
                  {meal.description && (
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-1">
                      {meal.description}
                    </p>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
