import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { routines as routinesApi, profiles as profilesApi } from "@/api/endpoints";
import { useHouseholdStore } from "@/stores/householdStore";
import EmojiPicker from "@/components/shared/EmojiPicker";
import type { Routine, RoutineTemplate } from "@/types";

/** Convert "HH:MM" or "HH:MM:SS" (24h) → { hour12, minute, period } */
function parse24(value: string): { hour12: number; minute: number; period: "AM" | "PM" } {
  if (!value) return { hour12: 12, minute: 0, period: "AM" };
  const [hStr, mStr] = value.split(":");
  let h = parseInt(hStr, 10);
  const m = parseInt(mStr, 10) || 0;
  const period: "AM" | "PM" = h >= 12 ? "PM" : "AM";
  if (h === 0) h = 12;
  else if (h > 12) h -= 12;
  return { hour12: h, minute: m, period };
}

/** Convert { hour12, minute, period } → "HH:MM" (24h) for the API */
function to24(hour12: number, minute: number, period: "AM" | "PM"): string {
  let h = hour12;
  if (period === "AM" && h === 12) h = 0;
  else if (period === "PM" && h !== 12) h += 12;
  return `${String(h).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
}

const HOURS = [12, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11];
const MINUTES = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55];

function TimePicker({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const parsed = parse24(value);
  const [hour, setHour] = useState(parsed.hour12);
  const [minute, setMinute] = useState(parsed.minute);
  const [period, setPeriod] = useState<"AM" | "PM">(parsed.period);
  const hasValue = !!value;

  const emit = (h: number, m: number, p: "AM" | "PM") => onChange(to24(h, m, p));

  const selCls = (active: boolean) =>
    `min-h-[44px] min-w-[44px] rounded-xl border-2 px-3 py-2 text-sm font-semibold transition active:scale-95 ${
      active
        ? "border-blue-500 bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
        : "border-gray-200 bg-white hover:border-gray-300 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300"
    }`;

  return (
    <div className="space-y-3">
      {/* Hour */}
      <div>
        <span className="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">Hour</span>
        <div className="flex flex-wrap gap-1.5">
          {HOURS.map((h) => (
            <button
              key={h}
              type="button"
              onClick={() => { setHour(h); emit(h, minute, period); }}
              className={selCls(hasValue && hour === h)}
            >
              {h}
            </button>
          ))}
        </div>
      </div>
      {/* Minute */}
      <div>
        <span className="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">Minute</span>
        <div className="flex flex-wrap gap-1.5">
          {MINUTES.map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => { setMinute(m); emit(hour, m, period); }}
              className={selCls(hasValue && minute === m)}
            >
              :{String(m).padStart(2, "0")}
            </button>
          ))}
        </div>
      </div>
      {/* AM / PM */}
      <div className="flex items-center gap-2">
        {(["AM", "PM"] as const).map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => { setPeriod(p); emit(hour, minute, p); }}
            className={selCls(hasValue && period === p)}
          >
            {p}
          </button>
        ))}
        {hasValue && (
          <button
            type="button"
            onClick={() => { onChange(""); }}
            className="ml-auto text-sm text-gray-400 hover:text-red-500"
          >
            Clear
          </button>
        )}
      </div>
    </div>
  );
}

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
  // null = inherit from the routine (run on every day the routine runs).
  // A non-null subset of the routine's days narrows the step to those days.
  days_of_week: number[] | null;
  // True = step is hidden on weekends, federal holidays, and admin-marked
  // school closures (e.g. "pack backpack" doesn't apply on snow days).
  school_day_only: boolean;
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
  template?: RoutineTemplate;
  onClose: () => void;
  onSaved: () => void;
  onDeleted?: () => void;
  onBack?: () => void;
}

let stepKeyCounter = 0;
function newStepKey() {
  return `step-${++stepKeyCounter}-${Date.now()}`;
}

export default function RoutineForm({
  routine,
  template,
  onClose,
  onSaved,
  onDeleted,
  onBack,
}: Props) {
  const queryClient = useQueryClient();
  const householdId = useHouseholdStore((s) => s.householdId);
  const isEditing = !!routine;

  const [name, setName] = useState(routine?.name ?? template?.name ?? "");
  const [timeBlock, setTimeBlock] = useState<TimeBlock>(
    routine?.time_block ?? template?.time_block ?? "morning",
  );
  const [daysOfWeek, setDaysOfWeek] = useState<number[]>(
    routine?.days_of_week ?? template?.days_of_week ?? [0, 1, 2, 3, 4, 5, 6],
  );
  const [startTime, setStartTime] = useState(routine?.start_time ?? "");
  const [profileId, setProfileId] = useState(routine?.profile_id ?? "");
  const [pausableOnVacation, setPausableOnVacation] = useState<boolean>(
    routine?.pausable_on_vacation ?? true,
  );
  const [steps, setSteps] = useState<StepInput[]>(() => {
    if (routine) {
      return routine.steps.map((s) => ({
        key: s.id,
        label: s.label,
        icon: s.icon ?? "",
        points_value: s.points_value ?? 0,
        days_of_week: s.days_of_week ?? null,
        school_day_only: s.school_day_only ?? false,
      }));
    }
    if (template) {
      return template.steps.map((s) => ({
        key: newStepKey(),
        label: s.label,
        icon: s.icon ?? "",
        points_value: s.points_value ?? 0,
        days_of_week: null,
        school_day_only: false,
      }));
    }
    return [
      {
        key: newStepKey(),
        label: "",
        icon: "",
        points_value: 0,
        days_of_week: null,
        school_day_only: false,
      },
    ];
  });

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
    setSteps((prev) => [
      ...prev,
      {
        key: newStepKey(),
        label: "",
        icon: "",
        points_value: 0,
        days_of_week: null,
        school_day_only: false,
      },
    ]);

  const removeStep = (key: string) =>
    setSteps((prev) => prev.filter((s) => s.key !== key));

  const updateStep = (key: string, field: keyof StepInput, value: string) => {
    setSteps((prev) =>
      prev.map((s) => (s.key === key ? { ...s, [field]: value } : s)),
    );
  };

  const toggleStepDay = (key: string, day: number) => {
    setSteps((prev) =>
      prev.map((s) => {
        if (s.key !== key) return s;
        // First click on a step that's "inherit" copies the routine's days
        // so the user is narrowing from the full set rather than starting empty.
        const base = s.days_of_week ?? daysOfWeek;
        const next = base.includes(day)
          ? base.filter((d) => d !== day)
          : [...base, day].sort();
        // If the user re-selects the full routine set, snap back to inherit.
        const isFullSet =
          next.length === daysOfWeek.length &&
          daysOfWeek.every((d) => next.includes(d));
        return { ...s, days_of_week: isFullSet ? null : next };
      }),
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
        // Only persist a step-level filter when it's actually narrower
        // than the routine; null means "every routine day".
        days_of_week: s.days_of_week,
        school_day_only: s.school_day_only,
      }));

    saveMutation.mutate({
      name: name.trim(),
      time_block: timeBlock,
      days_of_week: daysOfWeek,
      start_time: startTime || undefined,
      profile_id: profileId || undefined,
      pausable_on_vacation: pausableOnVacation,
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
        <span className="mb-2 block text-sm font-medium">
          Start Time{" "}
          <span className="text-gray-400">(optional)</span>
        </span>
        <TimePicker value={startTime} onChange={setStartTime} />
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
        <div className="mb-2 flex items-center justify-between">
          <span className="block text-sm font-medium">Steps</span>
          {steps.length > 0 && (() => {
            const allOn = steps.every((s) => s.school_day_only);
            return (
              <button
                type="button"
                onClick={() =>
                  setSteps((prev) =>
                    prev.map((s) => ({ ...s, school_day_only: !allOn }))
                  )
                }
                className="rounded-md px-2 py-1 text-xs font-semibold text-blue-700 hover:bg-blue-50 dark:text-blue-300 dark:hover:bg-blue-900/30"
                title="Toggle 'Only on school days' for every step at once"
              >
                {allOn ? "✓ Mark all as everyday" : "🎒 Mark all school-day only"}
              </button>
            );
          })()}
        </div>
        <div className="space-y-2">
          {steps.map((step, index) => {
            const stepDays = step.days_of_week ?? daysOfWeek;
            const isCustomized = step.days_of_week !== null;
            return (
              <div
                key={step.key}
                className="rounded-xl border border-transparent bg-gray-50 p-2 dark:bg-gray-800/40"
              >
                <div className="flex items-center gap-2">
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
                  <EmojiPicker
                    value={step.icon}
                    onChange={(v) => updateStep(step.key, "icon", v)}
                    placeholder="🪥"
                    ariaLabel={`Icon for step ${index + 1}`}
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

                {/* Per-step day filter — defaults to "every routine day" (chips
                    match the parent routine's days_of_week). Tap any chip to
                    narrow this step to specific days only. */}
                <div className="mt-2 flex items-center gap-2 pl-7 text-xs">
                  <span className="text-gray-400">On:</span>
                  <div className="flex gap-1">
                    {DAYS.map((label, i) => {
                      const inRoutine = daysOfWeek.includes(i);
                      const active = stepDays.includes(i);
                      return (
                        <button
                          key={i}
                          type="button"
                          disabled={!inRoutine}
                          onClick={() => toggleStepDay(step.key, i)}
                          className={`min-h-[28px] min-w-[28px] rounded-md border text-[11px] font-semibold transition ${
                            !inRoutine
                              ? "cursor-not-allowed border-gray-200 text-gray-300 dark:border-gray-700 dark:text-gray-600"
                              : active
                                ? "border-blue-500 bg-blue-500 text-white"
                                : "border-gray-300 text-gray-500 hover:border-blue-400 dark:border-gray-600"
                          }`}
                          title={
                            !inRoutine
                              ? "Add this day at the routine level first"
                              : undefined
                          }
                        >
                          {label}
                        </button>
                      );
                    })}
                  </div>
                  {isCustomized && (
                    <button
                      type="button"
                      onClick={() =>
                        setSteps((prev) =>
                          prev.map((s) =>
                            s.key === step.key ? { ...s, days_of_week: null } : s,
                          ),
                        )
                      }
                      className="text-[11px] text-gray-400 underline hover:text-gray-600"
                    >
                      reset
                    </button>
                  )}
                </div>

                {/* School-day-only toggle — hides this step on weekends,
                    US federal holidays, and admin-marked school closures
                    (snow days etc.). Useful for "pack backpack", "lunchbox". */}
                <label className="mt-2 flex items-center gap-2 pl-7 text-xs text-gray-500 dark:text-gray-400">
                  <input
                    type="checkbox"
                    checked={step.school_day_only}
                    onChange={(e) =>
                      setSteps((prev) =>
                        prev.map((s) =>
                          s.key === step.key
                            ? { ...s, school_day_only: e.target.checked }
                            : s,
                        ),
                      )
                    }
                    className="h-4 w-4 rounded border-gray-300 text-blue-500 focus:ring-blue-400"
                  />
                  <span>
                    Only on school days
                    <span
                      className="ml-1 cursor-help text-gray-400"
                      title="Skipped on weekends, US federal holidays, and admin-marked school closures."
                    >
                      ⓘ
                    </span>
                  </span>
                </label>
              </div>
            );
          })}
        </div>

        <button
          type="button"
          onClick={addStep}
          className="mt-2 min-h-[44px] w-full rounded-xl border-2 border-dashed border-gray-300 py-2 text-sm font-medium text-gray-500 hover:border-gray-400 hover:text-gray-600 dark:border-gray-600 dark:hover:border-gray-500"
        >
          + Add Step
        </button>
      </div>

      {/* Vacation pauseability (Phase C) */}
      <label className="flex items-start gap-3 rounded-xl bg-gray-50 dark:bg-gray-800/50 p-3 text-sm">
        <input
          type="checkbox"
          className="mt-0.5 h-4 w-4 rounded"
          checked={pausableOnVacation}
          onChange={(e) => setPausableOnVacation(e.target.checked)}
        />
        <span className="text-gray-700 dark:text-gray-300">
          Pause on vacation
          <span className="block text-xs text-gray-500 dark:text-gray-400">
            When admins start Vacation Mode, this routine will be suspended.
            Uncheck for medications or anything that must keep running.
          </span>
        </span>
      </label>

      {/* Actions */}
      <div className="flex gap-3 pt-2">
        {onBack && (
          <button
            type="button"
            onClick={onBack}
            className="min-h-[48px] rounded-xl border border-gray-300 px-4 font-semibold text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
            aria-label="Back to templates"
          >
            ← Templates
          </button>
        )}
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
