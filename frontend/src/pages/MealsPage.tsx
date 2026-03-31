import MealPlanner from "@/components/meals/MealPlanner";
import TodaysMeals from "@/components/meals/TodaysMeals";

export default function MealsPage() {
  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
        Meal Planning
      </h1>
      <TodaysMeals />
      <MealPlanner />
    </div>
  );
}
