import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { routines as routinesApi } from "@/api/endpoints";
import { useHouseholdStore } from "@/stores/householdStore";
import type { Routine, RoutineStep } from "@/types";
import LoadingSpinner from "@/components/shared/LoadingSpinner";
import EmptyState from "@/components/shared/EmptyState";
import Modal from "@/components/shared/Modal";
import RoutineStepper from "./RoutineStepper";
import RoutineForm from "./RoutineForm";

export type { Routine, RoutineStep };

type TimeBlock = Routine["time_block"];

const TIME_BLOCK_META: Record<
  TimeBlock,
  { label: string; icon: string }
> = {
  morning:   { label: "Morning",   icon: "🌅" },
  afternoon: { label: "Afternoon", icon: "☀️" },
  evening:   { label: "Evening",   icon: "🌇" },
  bedtime:   { label: "Bedtime",   icon: "🌙" },
};

function currentTimeBlock(): TimeBlock {
  const h = new Date().getHours();
  if (h >= 5 && h < 12) return "morning";
  if (h >= 12 && h < 17) return "afternoon";
  if (h >= 17 && h < 21) return "evening";
  return "bedtime";
}

export default function RoutineList() {
  const queryClient = useQueryClient();
  const householdId = useHouseholdStore((s) => s.householdId);
  const storeProfiles = useHouseholdStore((s) => s.profiles);
  const [selectedRoutine, setSelectedRoutine] = useState<Routine | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editingRoutine, setEditingRoutine] = useState<Routine | null>(null);

  const { data: routines = [], isLoading, error } = useQuery<Routine[]>({
    queryKey: ["routines", householdId],
    queryFn: async () => (await routinesApi.getAll(householdId!)).data,
    enabled: !!householdId,
  });

  const toggleMutation = useMutation({
    mutationFn: (routine: Routine) =>
      routinesApi.update(routine.id, { is_active: !routine.is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["routines"] }),
  });

  const activeBlock = currentTimeBlock();

  const grouped = (["morning", "afternoon", "evening", "bedtime"] as TimeBlock[]).map(
    (block) => ({
      block,
      ...TIME_BLOCK_META[block],
      routines: routines.filter((r) => r.time_block === block),
    }),
  );

  // ── Full-screen stepper overlay ──
  if (selectedRoutine) {
    return (
      <RoutineStepper
        routine={selectedRoutine}
        onClose={() => {
          setSelectedRoutine(null);
          queryClient.invalidateQueries({ queryKey: ["routines"] });
        }}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Routines</h1>
        <button
          onClick={() => setShowForm(true)}
          className="touch-target rounded-xl bg-[var(--color-accent,theme(colors.blue.600))] px-5 py-2 font-semibold text-white shadow transition hover:opacity-90 active:scale-95"
        >
          + Add Routine
        </button>
      </div>

      {isLoading && <LoadingSpinner message="Loading routines…" />}

      {error && (
        <div className="rounded-xl bg-red-50 p-4 text-red-700 dark:bg-red-900/30 dark:text-red-300">
          Failed to load routines. Please try again.
        </div>
      )}

      {/* Time-block groups */}
      {grouped.map(({ block, label, icon, routines: blockRoutines }) =>
        blockRoutines.length === 0 ? null : (
          <section key={block}>
            <h2
              className={`mb-3 flex items-center gap-2 text-lg font-semibold ${
                block === activeBlock
                  ? "text-blue-600 dark:text-blue-400"
                  : ""
              }`}
            >
              <span>{icon}</span> {label}
              {block === activeBlock && (
                <span className="ml-2 rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/40 dark:text-blue-300">
                  Now
                </span>
              )}
            </h2>

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {blockRoutines.map((routine) => {
                const profile = storeProfiles.find((p) => p.id === routine.profile_id);
                return (
                  <div
                    key={routine.id}
                    className={`group relative flex cursor-pointer flex-col rounded-2xl border-2 bg-white p-4 shadow-sm transition hover:shadow-md active:scale-[0.98] dark:bg-gray-800 ${
                      block === activeBlock && routine.is_active
                        ? "border-blue-500 dark:border-blue-400"
                        : "border-gray-200 dark:border-gray-700"
                    }`}
                    onClick={() => setSelectedRoutine(routine)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) =>
                      e.key === "Enter" && setSelectedRoutine(routine)
                    }
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h3 className="text-base font-semibold">
                          {routine.name}
                        </h3>
                        {profile && (
                          <div className="mt-1 flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                            {profile.avatar_url ? (
                              <img
                                src={profile.avatar_url}
                                alt={profile.name}
                                className="h-5 w-5 rounded-full object-cover"
                              />
                            ) : (
                              <span
                                className="flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold text-white"
                                style={{
                                  backgroundColor:
                                    profile.color ?? "#8b5cf6",
                                }}
                              >
                                {profile.name.charAt(0)}
                              </span>
                            )}
                            <span>{profile.name}</span>
                          </div>
                        )}
                      </div>

                      {/* Active toggle */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleMutation.mutate(routine);
                        }}
                        className={`touch-target rounded-full p-2 transition ${
                          routine.is_active
                            ? "text-green-600 dark:text-green-400"
                            : "text-gray-400 dark:text-gray-500"
                        }`}
                        aria-label={
                          routine.is_active
                            ? "Deactivate routine"
                            : "Activate routine"
                        }
                      >
                        {routine.is_active ? (
                          <svg
                            className="h-6 w-6"
                            fill="currentColor"
                            viewBox="0 0 20 20"
                          >
                            <path
                              fillRule="evenodd"
                              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                              clipRule="evenodd"
                            />
                          </svg>
                        ) : (
                          <svg
                            className="h-6 w-6"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <circle cx="12" cy="12" r="10" strokeWidth="2" />
                          </svg>
                        )}
                      </button>
                    </div>

                    <div className="mt-3 text-xs text-gray-400 dark:text-gray-500">
                      {routine.steps.length} step
                      {routine.steps.length !== 1 ? "s" : ""}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        ),
      )}

      {!isLoading && routines.length === 0 && (
        <EmptyState
          icon="📋"
          title="No routines yet"
          description='Tap "Add Routine" to get started'
          action={{ label: "Add Routine", onClick: () => setShowForm(true) }}
        />
      )}

      {/* Create / Edit modal */}
      <Modal
        open={showForm || !!editingRoutine}
        onClose={() => {
          setShowForm(false);
          setEditingRoutine(null);
        }}
        title={editingRoutine ? "Edit Routine" : "New Routine"}
      >
        <RoutineForm
          routine={editingRoutine ?? undefined}
          onClose={() => {
            setShowForm(false);
            setEditingRoutine(null);
          }}
          onSaved={() => {
            setShowForm(false);
            setEditingRoutine(null);
            queryClient.invalidateQueries({ queryKey: ["routines"] });
          }}
        />
      </Modal>
    </div>
  );
}
