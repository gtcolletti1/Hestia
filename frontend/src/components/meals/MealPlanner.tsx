import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  startOfWeek,
  endOfWeek,
  addWeeks,
  subWeeks,
  addDays,
  format,
  isToday,
} from "date-fns";
import { meals, profiles as profilesApi } from "@/api/endpoints";
import { useHouseholdStore } from "@/stores/householdStore";
import MealForm from "./MealForm";
import type { MealPlan, Profile } from "@/types";

const MEAL_TYPES: MealPlan["meal_type"][] = [
  "breakfast",
  "lunch",
  "dinner",
  "snack",
];

const MEAL_EMOJI: Record<MealPlan["meal_type"], string> = {
  breakfast: "🌅",
  lunch: "☀️",
  dinner: "🌙",
  snack: "🍿",
};

export default function MealPlanner() {
  const householdId = useHouseholdStore((s) => s.householdId);

  const [weekStart, setWeekStart] = useState(() =>
    startOfWeek(new Date(), { weekStartsOn: 1 }),
  );
  const [formState, setFormState] = useState<{
    open: boolean;
    meal?: MealPlan;
    date?: string;
    mealType?: MealPlan["meal_type"];
  }>({ open: false });

  const weekEnd = endOfWeek(weekStart, { weekStartsOn: 1 });
  const weekStartStr = format(weekStart, "yyyy-MM-dd");
  const weekEndStr = format(weekEnd, "yyyy-MM-dd");

  const weekDays = useMemo(
    () => Array.from({ length: 7 }, (_, i) => addDays(weekStart, i)),
    [weekStart],
  );

  const { data: mealsData = [] } = useQuery({
    queryKey: ["meals", "weekly", householdId, weekStartStr, weekEndStr],
    queryFn: () =>
      meals
        .getAll(householdId!, {
          start_date: weekStartStr,
          end_date: weekEndStr,
        })
        .then((r) => r.data),
    enabled: !!householdId,
  });

  const { data: profilesData = [] } = useQuery({
    queryKey: ["profiles", householdId],
    queryFn: () => profilesApi.getAll(householdId!).then((r) => r.data),
    enabled: !!householdId,
  });

  const mealMap = useMemo(() => {
    const map = new Map<string, MealPlan>();
    mealsData.forEach((m) => {
      map.set(`${m.date}:${m.meal_type}`, m);
    });
    return map;
  }, [mealsData]);

  const getMeal = (day: Date, type: MealPlan["meal_type"]) =>
    mealMap.get(`${format(day, "yyyy-MM-dd")}:${type}`);

  const getCook = (profileId?: string): Profile | undefined =>
    profileId ? profilesData.find((p) => p.id === profileId) : undefined;

  const openForm = (day: Date, type: MealPlan["meal_type"]) => {
    const existing = getMeal(day, type);
    setFormState({
      open: true,
      meal: existing,
      date: format(day, "yyyy-MM-dd"),
      mealType: type,
    });
  };

  return (
    <div className="space-y-4">
      {/* Week navigation */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => setWeekStart((w) => subWeeks(w, 1))}
          className="rounded-xl bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 p-3 min-h-[44px] min-w-[44px] flex items-center justify-center transition-colors"
          aria-label="Previous week"
        >
          ←
        </button>
        <div className="text-center">
          <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">
            {format(weekStart, "MMM d")} – {format(weekEnd, "MMM d, yyyy")}
          </h2>
          <button
            onClick={() =>
              setWeekStart(startOfWeek(new Date(), { weekStartsOn: 1 }))
            }
            className="text-sm text-blue-600 dark:text-blue-400 hover:underline mt-0.5"
          >
            Today
          </button>
        </div>
        <button
          onClick={() => setWeekStart((w) => addWeeks(w, 1))}
          className="rounded-xl bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 p-3 min-h-[44px] min-w-[44px] flex items-center justify-center transition-colors"
          aria-label="Next week"
        >
          →
        </button>
      </div>

      {/* Weekly grid */}
      <div className="grid grid-cols-7 gap-2 overflow-x-auto">
        {weekDays.map((day) => {
          const today = isToday(day);
          return (
            <div
              key={day.toISOString()}
              className={`rounded-xl border p-2 min-w-[120px] ${
                today
                  ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20 ring-2 ring-blue-500/30"
                  : "border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
              }`}
            >
              {/* Day header */}
              <div className="text-center mb-2 pb-2 border-b border-gray-200 dark:border-gray-700">
                <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  {format(day, "EEE")}
                </div>
                <div
                  className={`text-lg font-bold ${
                    today
                      ? "text-blue-600 dark:text-blue-400"
                      : "text-gray-900 dark:text-gray-100"
                  }`}
                >
                  {format(day, "d")}
                </div>
              </div>

              {/* Meal slots */}
              <div className="space-y-1.5">
                {MEAL_TYPES.map((type) => {
                  const meal = getMeal(day, type);
                  const cook = meal
                    ? getCook(meal.assigned_profile_id)
                    : undefined;
                  return (
                    <button
                      key={type}
                      onClick={() => openForm(day, type)}
                      className={`w-full text-left rounded-lg p-2 min-h-[44px] transition-colors text-sm ${
                        meal
                          ? "bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600"
                          : "bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 border border-dashed border-gray-300 dark:border-gray-600"
                      }`}
                    >
                      <div className="flex items-center gap-1">
                        <span className="text-xs">{MEAL_EMOJI[type]}</span>
                        {meal ? (
                          <div className="flex items-center gap-1 min-w-0">
                            {cook && (
                              <span
                                className="h-2 w-2 rounded-full shrink-0"
                                style={{ backgroundColor: cook.color }}
                              />
                            )}
                            <span className="truncate font-medium text-gray-900 dark:text-gray-100">
                              {meal.title}
                            </span>
                          </div>
                        ) : (
                          <span className="text-gray-400 dark:text-gray-500">
                            +
                          </span>
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Meal Form Modal */}
      {formState.open && (
        <MealForm
          meal={formState.meal}
          initialDate={formState.date}
          initialType={formState.mealType}
          profiles={profilesData}
          onClose={() => setFormState({ open: false })}
          onSaved={() => setFormState({ open: false })}
        />
      )}
    </div>
  );
}
