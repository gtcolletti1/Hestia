import { useState, useEffect, useCallback } from "react";
import { format, parseISO } from "date-fns";
import { formatTime } from "@/utils/timeFormat";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { events as eventsApi, reminders as remindersApi } from "@/api/endpoints";
import { useHouseholdStore } from "@/stores/householdStore";
import { useHouseholdSettings } from "@/hooks/useHouseholdSettings";
import type { CalendarEvent, EventFormData } from "./types";
import { RECURRENCE_OPTIONS, recurrenceLabel } from "./types";

interface EventModalProps {
  event: CalendarEvent | null;
  onClose: () => void;
  profiles?: { id: string; name: string; color: string }[];
}

function toLocalDatetime(iso: string): string {
  return format(parseISO(iso), "yyyy-MM-dd'T'HH:mm");
}

const EMPTY_FORM: EventFormData = {
  title: "",
  start: "",
  end: "",
  location: "",
  description: "",
  profile_id: "",
  all_day: false,
  recurrence_rule: "",
};

export default function EventModal({ event, onClose, profiles = [] }: EventModalProps) {
  const queryClient = useQueryClient();
  const householdId = useHouseholdStore((s) => s.householdId);
  const { timeFormat } = useHouseholdSettings();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<EventFormData>(EMPTY_FORM);
  const [reminderMinutes, setReminderMinutes] = useState<string>("");

  useEffect(() => {
    if (event) {
      setForm({
        title: event.title,
        start: toLocalDatetime(event.start),
        end: toLocalDatetime(event.end),
        location: event.location ?? "",
        description: event.description ?? "",
        profile_id: event.profile_id,
        all_day: event.all_day ?? false,
        recurrence_rule: event.recurrence_rule ?? "",
      });
      setEditing(false);
    }
  }, [event]);

  const updateMutation = useMutation({
    mutationFn: async (data: EventFormData) => {
      await eventsApi.update(event!.id, {
        title: data.title,
        start_time: data.start,
        end_time: data.end,
        location: data.location,
        description: data.description,
        profile_id: data.profile_id || undefined,
        all_day: data.all_day,
        recurrence_rule: data.recurrence_rule || undefined,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["events"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      onClose();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async () => {
      await eventsApi.delete(event!.id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["events"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      onClose();
    },
  });

  const handleChange = useCallback(
    (field: keyof EventFormData, value: string | boolean) => {
      setForm((prev) => ({ ...prev, [field]: value }));
    },
    [],
  );

  const handleSave = async () => {
    if (!form.title.trim()) return;
    updateMutation.mutate(form);

    // Create reminder if selected
    if (reminderMinutes && event && householdId) {
      try {
        await remindersApi.create({
          event_id: event.id,
          minutes_before: parseInt(reminderMinutes, 10),
          household_id: householdId,
        });
      } catch {
        // silently ignore reminder creation errors
      }
    }
  };

  if (!event) return null;

  const isBusy = updateMutation.isPending || deleteMutation.isPending;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
    >
      <div
        className="w-full max-w-lg rounded-2xl bg-white dark:bg-gray-800 shadow-xl overflow-y-auto max-h-[90vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 px-6 py-4">
          <h2 className="text-xl font-bold truncate">
            {editing ? "Edit Event" : <span className="privacy-blur">{event.title}</span>}
          </h2>
          <button
            className="min-h-[44px] min-w-[44px] flex items-center justify-center rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500"
            onClick={onClose}
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <div className="px-6 py-4 space-y-4">
          {editing ? (
            /* ── Edit mode ── */
            <>
              <label className="block">
                <span className="text-sm font-medium text-gray-600 dark:text-gray-300">
                  Title
                </span>
                <input
                  type="text"
                  value={form.title}
                  onChange={(e) => handleChange("title", e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent px-3 py-3 text-base min-h-[44px]"
                />
              </label>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <label className="block">
                  <span className="text-sm font-medium text-gray-600 dark:text-gray-300">
                    Start
                  </span>
                  <input
                    type="datetime-local"
                    value={form.start}
                    onChange={(e) => handleChange("start", e.target.value)}
                    className="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent px-3 py-3 text-base min-h-[44px]"
                  />
                </label>
                <label className="block">
                  <span className="text-sm font-medium text-gray-600 dark:text-gray-300">
                    End
                  </span>
                  <input
                    type="datetime-local"
                    value={form.end}
                    onChange={(e) => handleChange("end", e.target.value)}
                    className="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent px-3 py-3 text-base min-h-[44px]"
                  />
                </label>
              </div>

              <label className="block">
                <span className="text-sm font-medium text-gray-600 dark:text-gray-300">
                  Location
                </span>
                <input
                  type="text"
                  value={form.location}
                  onChange={(e) => handleChange("location", e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent px-3 py-3 text-base min-h-[44px]"
                />
              </label>

              <label className="block">
                <span className="text-sm font-medium text-gray-600 dark:text-gray-300">
                  Description
                </span>
                <textarea
                  value={form.description}
                  onChange={(e) => handleChange("description", e.target.value)}
                  rows={3}
                  className="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent px-3 py-3 text-base min-h-[44px]"
                />
              </label>

              {profiles.length > 0 && (
                <label className="block">
                  <span className="text-sm font-medium text-gray-600 dark:text-gray-300">
                    Profile
                  </span>
                  <select
                    value={form.profile_id}
                    onChange={(e) => handleChange("profile_id", e.target.value)}
                    className="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent px-3 py-3 text-base min-h-[44px]"
                  >
                    <option value="">Select profile</option>
                    {profiles.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                </label>
              )}

              <label className="block">
                <span className="text-sm font-medium text-gray-600 dark:text-gray-300">
                  Repeat
                </span>
                <select
                  value={form.recurrence_rule}
                  onChange={(e) => handleChange("recurrence_rule", e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent px-3 py-3 text-base min-h-[44px]"
                >
                  {RECURRENCE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block">
                <span className="text-sm font-medium text-gray-600 dark:text-gray-300">
                  🔔 Reminder
                </span>
                <select
                  value={reminderMinutes}
                  onChange={(e) => setReminderMinutes(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent px-3 py-3 text-base min-h-[44px]"
                >
                  <option value="">No reminder</option>
                  <option value="5">5 minutes before</option>
                  <option value="15">15 minutes before</option>
                  <option value="30">30 minutes before</option>
                  <option value="60">1 hour before</option>
                  <option value="1440">1 day before</option>
                </select>
              </label>
            </>
          ) : (
            /* ── View mode ── */
            <>
              <div className="flex items-center gap-2">
                <span
                  className="h-4 w-4 rounded-full shrink-0"
                  style={{ backgroundColor: event.profile_color }}
                />
                <span className="text-sm text-gray-500 dark:text-gray-400 privacy-blur">
                  {event.profile_name}
                </span>
              </div>

              <div className="space-y-2 text-sm">
                <p>
                  <span className="font-medium">When: </span>
                  {formatTime(parseISO(event.start), "EEE, MMM d · h:mm a", timeFormat)}
                  {" – "}
                  {formatTime(parseISO(event.end), "h:mm a", timeFormat)}
                </p>
                {event.location && (
                  <p>
                    <span className="font-medium">Where: </span>
                    <span className="privacy-blur">{event.location}</span>
                  </p>
                )}
                {event.recurrence_rule && (
                  <p>
                    <span className="font-medium">🔁 </span>
                    {recurrenceLabel(event.recurrence_rule)}
                  </p>
                )}
                {event.description && (
                  <p className="text-gray-600 dark:text-gray-300 whitespace-pre-wrap privacy-blur">
                    {event.description}
                  </p>
                )}
                {event.calendar_source && (
                  <p className="text-gray-400 text-xs">
                    Source: {event.calendar_source}
                  </p>
                )}
              </div>
            </>
          )}
        </div>

        {/* Actions */}
        <div className="flex flex-wrap items-center gap-3 border-t border-gray-200 dark:border-gray-700 px-6 py-4">
          {editing ? (
            <>
              <button
                onClick={handleSave}
                disabled={isBusy}
                className="min-h-[44px] flex-1 rounded-lg bg-blue-600 text-white font-medium px-4 py-2 hover:bg-blue-700 disabled:opacity-50"
              >
                {updateMutation.isPending ? "Saving…" : "Save"}
              </button>
              <button
                onClick={() => setEditing(false)}
                disabled={isBusy}
                className="min-h-[44px] flex-1 rounded-lg border border-gray-300 dark:border-gray-600 font-medium px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50"
              >
                Cancel
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() => setEditing(true)}
                className="min-h-[44px] flex-1 rounded-lg bg-blue-600 text-white font-medium px-4 py-2 hover:bg-blue-700"
              >
                Edit
              </button>
              <button
                onClick={() => deleteMutation.mutate()}
                disabled={isBusy}
                className="min-h-[44px] flex-1 rounded-lg bg-red-600 text-white font-medium px-4 py-2 hover:bg-red-700 disabled:opacity-50"
              >
                {deleteMutation.isPending ? "Deleting…" : "Delete"}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
