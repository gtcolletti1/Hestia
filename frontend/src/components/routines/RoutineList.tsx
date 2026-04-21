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

  const deleteMutation = useMutation({
    mutationFn: (routineId: string) => routinesApi.delete(routineId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["routines"] }),
  });

  const duplicateMutation = useMutation({
    mutationFn: (routineId: string) => routinesApi.duplicate(routineId),
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

                    <div className="mt-3 flex items-center justify-between">
                      <span className="text-xs text-gray-400 dark:text-gray-500">
                        {routine.steps.length} step
                        {routine.steps.length !== 1 ? "s" : ""}
                      </span>
                      <div className="flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            duplicateMutation.mutate(routine.id);
                          }}
                          className="touch-target rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-green-600 dark:hover:bg-gray-700 dark:hover:text-green-400"
                          aria-label="Duplicate routine"
                          title="Duplicate"
                        >
                          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 01-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H6.75a9.06 9.06 0 011.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161-7.5-8.876a9.06 9.06 0 00-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 01-1.125-1.125v-9.25m12 6.625v-1.875a3.375 3.375 0 00-3.375-3.375h-1.5a1.125 1.125 0 01-1.125-1.125v-1.5a3.375 3.375 0 00-3.375-3.375H9.75" />
                          </svg>
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setEditingRoutine(routine);
                          }}
                          className="touch-target rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-blue-600 dark:hover:bg-gray-700 dark:hover:text-blue-400"
                          aria-label="Edit routine"
                        >
                          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931z" />
                          </svg>
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            if (confirm(`Delete "${routine.name}"?`)) {
                              deleteMutation.mutate(routine.id);
                            }
                          }}
                          className="touch-target rounded-lg p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20 dark:hover:text-red-400"
                          aria-label="Delete routine"
                        >
                          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                          </svg>
                        </button>
                      </div>
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
          onDeleted={() => {
            setShowForm(false);
            setEditingRoutine(null);
            queryClient.invalidateQueries({ queryKey: ["routines"] });
          }}
        />
      </Modal>
    </div>
  );
}
