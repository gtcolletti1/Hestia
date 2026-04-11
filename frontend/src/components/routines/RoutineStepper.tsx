import { useState, useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { routines as routinesApi } from "@/api/endpoints";
import { useHouseholdStore } from "@/stores/householdStore";
import type { Routine, RoutineStep } from "@/types";
import StreakDisplay from "./StreakDisplay";

interface Props {
  routine: Routine;
  onClose: () => void;
}

export default function RoutineStepper({ routine, onClose }: Props) {
  const queryClient = useQueryClient();
  const profiles = useHouseholdStore((s) => s.profiles);
  const [selectedProfileId, setSelectedProfileId] = useState(
    routine.profile_id ?? profiles[0]?.id ?? "",
  );
  const [steps, setSteps] = useState<(RoutineStep & { completed: boolean })[]>(
    () =>
      [...routine.steps]
        .sort((a, b) => a.sort_order - b.sort_order)
        .map((s) => ({ ...s, completed: false })),
  );
  const [showCelebration, setShowCelebration] = useState(false);

  const completedCount = steps.filter((s) => s.completed).length;
  const totalCount = steps.length;
  const allDone = totalCount > 0 && completedCount === totalCount;

  useEffect(() => {
    if (allDone) setShowCelebration(true);
  }, [allDone]);

  const toggleStep = useMutation({
    mutationFn: async ({ stepId }: { stepId: string }) =>
      routinesApi.completeStep(routine.id, stepId, selectedProfileId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["routines"] });
      queryClient.invalidateQueries({
        queryKey: ["routine-streak", routine.id],
      });
    },
  });

  const handleToggle = (stepId: string) => {
    setSteps((prev) =>
      prev.map((s) =>
        s.id === stepId ? { ...s, completed: !s.completed } : s,
      ),
    );
    toggleStep.mutate({ stepId });
  };

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-white dark:bg-gray-900">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3 dark:border-gray-700">
        <button
          onClick={onClose}
          className="touch-target rounded-xl p-2 text-gray-600 hover:bg-gray-100 active:bg-gray-200 dark:text-gray-300 dark:hover:bg-gray-800"
          aria-label="Close"
        >
          <svg
            className="h-6 w-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 19l-7-7 7-7"
            />
          </svg>
        </button>
        <h1 className="text-lg font-bold">{routine.name}</h1>
        <div className="w-11" />
      </div>

      {/* Profile selector */}
      {profiles.length > 1 && (
        <div className="flex gap-2 overflow-x-auto px-4 py-2">
          {profiles.map((p) => (
            <button
              key={p.id}
              onClick={() => setSelectedProfileId(p.id)}
              className={`flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium transition active:scale-95 ${
                selectedProfileId === p.id
                  ? "bg-blue-600 text-white shadow"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300"
              }`}
            >
              <span
                className="flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold text-white"
                style={{ backgroundColor: p.color ?? "#8b5cf6" }}
              >
                {p.name.charAt(0)}
              </span>
              {p.name}
            </button>
          ))}
        </div>
      )}

      {/* Progress bar */}
      <div className="px-4 py-3">
        <div className="flex items-center justify-between text-sm font-medium text-gray-600 dark:text-gray-400">
          <span>
            {completedCount}/{totalCount} steps
          </span>
          <span>
            {totalCount > 0
              ? Math.round((completedCount / totalCount) * 100)
              : 0}
            %
          </span>
        </div>
        <div className="mt-1 h-3 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
          <div
            className="h-full rounded-full bg-green-500 transition-all duration-300"
            style={{
              width: `${totalCount > 0 ? (completedCount / totalCount) * 100 : 0}%`,
            }}
          />
        </div>
      </div>

      {/* Steps list */}
      <div className="flex-1 overflow-y-auto px-4 pb-4">
        <div className="space-y-3">
          {steps.map((step) => (
            <button
              key={step.id}
              onClick={() => handleToggle(step.id)}
              className={`flex min-h-[60px] w-full items-center gap-4 rounded-2xl border-2 p-4 text-left transition active:scale-[0.98] ${
                step.completed
                  ? "border-green-300 bg-green-50 dark:border-green-700 dark:bg-green-900/20"
                  : "border-gray-200 bg-white hover:border-gray-300 dark:border-gray-700 dark:bg-gray-800 dark:hover:border-gray-600"
              }`}
            >
              {/* Checkbox circle */}
              <div
                className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-2 transition ${
                  step.completed
                    ? "border-green-500 bg-green-500 text-white"
                    : "border-gray-300 dark:border-gray-600"
                }`}
              >
                {step.completed && (
                  <svg
                    className="h-5 w-5"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                )}
              </div>

              {/* Icon */}
              {step.icon && <span className="text-2xl">{step.icon}</span>}

              {/* Label */}
              <span
                className={`flex-1 text-base font-medium transition ${
                  step.completed
                    ? "text-gray-400 line-through dark:text-gray-500"
                    : "text-gray-800 dark:text-gray-100"
                }`}
              >
                {step.label}
              </span>
            </button>
          ))}
        </div>

        {/* Celebration */}
        {showCelebration && (
          <div className="mt-8 flex flex-col items-center gap-3 rounded-2xl bg-gradient-to-br from-yellow-100 to-green-100 p-8 text-center dark:from-yellow-900/30 dark:to-green-900/30">
            <span className="animate-bounce text-6xl">🎉</span>
            <h2 className="text-2xl font-bold text-green-700 dark:text-green-400">
              All done!
            </h2>
            <p className="text-gray-600 dark:text-gray-400">
              Great job finishing your routine!
            </p>
          </div>
        )}

        {/* Streak */}
        <div className="mt-6">
          <StreakDisplay routineId={routine.id} profileId={selectedProfileId} />
        </div>
      </div>
    </div>
  );
}
