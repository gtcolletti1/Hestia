import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { routines as routinesApi, profiles as profilesApi } from "@/api/endpoints";
import { useHouseholdStore } from "@/stores/householdStore";
import type { Routine } from "@/types";

interface ProfileOption {
  id: string;
  name: string;
  color?: string;
  avatar_url?: string;
}

interface StepInput {
  key: string;
  label: string;
  icon: string;
  points_value: number;
}

type TimeBlock = "morning" | "afternoon" | "evening" | "bedtime";

const TIME_BLOCKS: { value: TimeBlock; label: string; icon: string }[] = [
  { value: "morning", label: "Morning", icon: "🌅" },
  { value: "afternoon", label: "Afternoon", icon: "☀️" },
  { value: "evening", label: "Evening", icon: "🌇" },
  { value: "bedtime", label: "Bedtime", icon: "🌙" },
];

const DAYS = ["M", "T", "W", "T", "F", "S", "S"] as const;

interface Props {
  routine?: Routine;
  onClose: () => void;
  onSaved: () => void;
  onDeleted?: () => void;
}

let stepKeyCounter = 0;
function newStepKey() {
  return `step-${++stepKeyCounter}-${Date.now()}`;
}

export default function RoutineForm({ routine, onClose, onSaved, onDeleted }: Props) {
  const queryClient = useQueryClient();
  const householdId = useHouseholdStore((s) => s.householdId);
  const isEditing = !!routine;

  const [name, setName] = useState(routine?.name ?? "");
  const [timeBlock, setTimeBlock] = useState<TimeBlock>(
    routine?.time_block ?? "morning",
  );
  const [daysOfWeek, setDaysOfWeek] = useState<number[]>(
    routine?.days_of_week ?? [0, 1, 2, 3, 4, 5, 6],
  );
  const [startTime, setStartTime] = useState(routine?.start_time ?? "");
  const [profileId, setProfileId] = useState(routine?.profile_id ?? "");
  const [steps, setSteps] = useState<StepInput[]>(
    routine?.steps.map((s) => ({
      key: s.id,
      label: s.label,
      icon: s.icon ?? "",
      points_value: s.points_value ?? 0,
    })) ?? [{ key: newStepKey(), label: "", icon: "", points_value: 0 }],
  );

  const { data: profiles = [] } = useQuery<ProfileOption[]>({
    queryKey: ["profiles", householdId],
    queryFn: async () => (await profilesApi.getAll(householdId!)).data,
    enabled: !!householdId,
  });

  const saveMutation = useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      if (isEditing) {
        return routinesApi.update(routine.id, payload);
      }
      const { steps: rawSteps, ...rest } = payload;
      return routinesApi.create({
        ...rest,
        household_id: householdId!,
        steps: rawSteps,
      } as Parameters<typeof routinesApi.create>[0]);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["routines"] });
      onSaved();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => routinesApi.delete(routine!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["routines"] });
      if (onDeleted) onDeleted();
      else onClose();
    },
  });

  const toggleDay = (dayIndex: number) => {
    setDaysOfWeek((prev) =>
      prev.includes(dayIndex)
        ? prev.filter((d) => d !== dayIndex)
        : [...prev, dayIndex].sort(),
    );
  };

  const addStep = () =>
    setSteps((prev) => [...prev, { key: newStepKey(), label: "", icon: "", points_value: 0 }]);

  const removeStep = (key: string) =>
    setSteps((prev) => prev.filter((s) => s.key !== key));

  const updateStep = (key: string, field: keyof StepInput, value: string) => {
    setSteps((prev) =>
      prev.map((s) => (s.key === key ? { ...s, [field]: value } : s)),
    );
  };

  const moveStep = (index: number, direction: -1 | 1) => {
    const target = index + direction;
    if (target < 0 || target >= steps.length) return;
    setSteps((prev) => {
      const next = [...prev];
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const filteredSteps = steps
      .filter((s) => s.label.trim())
      .map((s, i) => ({
        label: s.label.trim(),
        icon: s.icon || undefined,
        sort_order: i,
        points_value: s.points_value,
      }));

    saveMutation.mutate({
      name: name.trim(),
      time_block: timeBlock,
      days_of_week: daysOfWeek,
      start_time: startTime || undefined,
      profile_id: profileId || undefined,
      steps: filteredSteps,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="max-h-[70vh] space-y-5 overflow-y-auto">
      {/* Name */}
      <div>
        <label htmlFor="routine-name" className="mb-1 block text-sm font-medium">
          Routine Name
        </label>
        <input
          id="routine-name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Morning Checklist"
          required
          className="touch-target w-full rounded-xl border border-gray-300 px-4 py-2 text-base focus:border-blue-500 focus:ring-2 focus:ring-blue-200 dark:border-gray-600 dark:bg-gray-800 dark:focus:ring-blue-800"
        />
      </div>

      {/* Time Block */}
      <div>
        <span className="mb-2 block text-sm font-medium">Time Block</span>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {TIME_BLOCKS.map((tb) => (
            <button
              key={tb.value}
              type="button"
              onClick={() => setTimeBlock(tb.value)}
              className={`min-h-[48px] rounded-xl border-2 px-3 py-2 text-sm font-semibold transition active:scale-95 ${
                timeBlock === tb.value
                  ? "border-blue-500 bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
                  : "border-gray-200 bg-white hover:border-gray-300 dark:border-gray-700 dark:bg-gray-800"
              }`}
            >
              {tb.icon} {tb.label}
            </button>
          ))}
        </div>
      </div>

      {/* Days of Week */}
      <div>
        <span className="mb-2 block text-sm font-medium">Days</span>
        <div className="flex gap-2">
          {DAYS.map((label, i) => (
            <button
              key={i}
              type="button"
              onClick={() => toggleDay(i)}
              className={`flex h-11 w-11 items-center justify-center rounded-full border-2 text-sm font-bold transition active:scale-95 ${
                daysOfWeek.includes(i)
                  ? "border-blue-500 bg-blue-500 text-white"
                  : "border-gray-300 text-gray-500 dark:border-gray-600 dark:text-gray-400"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Start Time */}
      <div>
        <label htmlFor="start-time" className="mb-1 block text-sm font-medium">
          Start Time{" "}
          <span className="text-gray-400">(optional)</span>
        </label>
        <input
          id="start-time"
          type="time"
          value={startTime}
          onChange={(e) => setStartTime(e.target.value)}
          className="touch-target rounded-xl border border-gray-300 px-4 py-2 text-base dark:border-gray-600 dark:bg-gray-800"
        />
      </div>

      {/* Profile Selector */}
      <div>
        <span className="mb-2 block text-sm font-medium">Assign To</span>
        <div className="flex flex-wrap gap-2">
          {profiles.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => setProfileId(p.id)}
              className={`flex min-h-[44px] items-center gap-2 rounded-xl border-2 px-4 py-2 text-sm font-medium transition active:scale-95 ${
                profileId === p.id
                  ? "border-blue-500 bg-blue-50 dark:bg-blue-900/30"
                  : "border-gray-200 dark:border-gray-700"
              }`}
            >
              {p.avatar_url ? (
                <img
                  src={p.avatar_url}
                  alt={p.name}
                  className="h-6 w-6 rounded-full object-cover"
                />
              ) : (
                <span
                  className="flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold text-white"
                  style={{ backgroundColor: p.color ?? "#8b5cf6" }}
                >
                  {p.name.charAt(0)}
                </span>
              )}
              {p.name}
            </button>
          ))}
          {profiles.length === 0 && (
            <p className="text-sm text-gray-400">No profiles found</p>
          )}
        </div>
      </div>

      {/* Steps Editor */}
      <div>
        <span className="mb-2 block text-sm font-medium">Steps</span>
        <div className="space-y-2">
          {steps.map((step, index) => (
            <div key={step.key} className="flex items-center gap-2">
              {/* Reorder */}
              <div className="flex flex-col">
                <button
                  type="button"
                  onClick={() => moveStep(index, -1)}
                  disabled={index === 0}
                  className="min-h-[22px] min-w-[22px] text-gray-400 hover:text-gray-600 disabled:opacity-30"
                  aria-label="Move up"
                >
                  ▲
                </button>
                <button
                  type="button"
                  onClick={() => moveStep(index, 1)}
                  disabled={index === steps.length - 1}
                  className="min-h-[22px] min-w-[22px] text-gray-400 hover:text-gray-600 disabled:opacity-30"
                  aria-label="Move down"
                >
                  ▼
                </button>
              </div>

              {/* Icon */}
              <input
                type="text"
                value={step.icon}
                onChange={(e) => updateStep(step.key, "icon", e.target.value)}
                placeholder="🪥"
                className="touch-target w-14 rounded-lg border border-gray-300 text-center text-lg dark:border-gray-600 dark:bg-gray-800"
                maxLength={4}
              />

              {/* Label */}
              <input
                type="text"
                value={step.label}
                onChange={(e) => updateStep(step.key, "label", e.target.value)}
                placeholder={`Step ${index + 1}`}
                className="touch-target flex-1 rounded-lg border border-gray-300 px-3 dark:border-gray-600 dark:bg-gray-800"
              />

              {/* Points */}
              <div className="flex items-center gap-1">
                <input
                  type="number"
                  min={0}
                  value={step.points_value}
                  onChange={(e) => {
                    const val = parseInt(e.target.value) || 0;
                    setSteps((prev) =>
                      prev.map((s) =>
                        s.key === step.key ? { ...s, points_value: val } : s,
                      ),
                    );
                  }}
                  className="touch-target w-14 rounded-lg border border-gray-300 text-center text-sm dark:border-gray-600 dark:bg-gray-800"
                  title="Points for completing this step"
                />
                <span className="text-xs text-gray-400">⭐</span>
              </div>

              {/* Remove */}
              <button
                type="button"
                onClick={() => removeStep(step.key)}
                disabled={steps.length <= 1}
                className="touch-target rounded-lg text-red-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-30 dark:hover:bg-red-900/20"
                aria-label="Remove step"
              >
                ✕
              </button>
            </div>
          ))}
        </div>

        <button
          type="button"
          onClick={addStep}
          className="mt-2 min-h-[44px] w-full rounded-xl border-2 border-dashed border-gray-300 py-2 text-sm font-medium text-gray-500 hover:border-gray-400 hover:text-gray-600 dark:border-gray-600 dark:hover:border-gray-500"
        >
          + Add Step
        </button>
      </div>

      {/* Actions */}
      <div className="flex gap-3 pt-2">
        <button
          type="button"
          onClick={onClose}
          className="min-h-[48px] flex-1 rounded-xl border border-gray-300 py-3 font-semibold text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={saveMutation.isPending || !name.trim()}
          className="min-h-[48px] flex-1 rounded-xl bg-blue-600 py-3 font-semibold text-white shadow hover:bg-blue-700 disabled:opacity-50"
        >
          {saveMutation.isPending
            ? "Saving…"
            : isEditing
              ? "Update"
              : "Create"}
        </button>
      </div>

      {saveMutation.isError && (
        <p className="text-center text-sm text-red-600 dark:text-red-400">
          Failed to save routine. Please try again.
        </p>
      )}

      {isEditing && (
        <button
          type="button"
          onClick={() => {
            if (confirm(`Delete "${routine.name}"? This cannot be undone.`)) {
              deleteMutation.mutate();
            }
          }}
          disabled={deleteMutation.isPending}
          className="mt-2 min-h-[48px] w-full rounded-xl bg-red-100 py-3 font-semibold text-red-600 hover:bg-red-200 disabled:opacity-50 dark:bg-red-900/30 dark:text-red-400 dark:hover:bg-red-900/50"
        >
          {deleteMutation.isPending ? "Deleting…" : "Delete Routine"}
        </button>
      )}
    </form>
  );
}
