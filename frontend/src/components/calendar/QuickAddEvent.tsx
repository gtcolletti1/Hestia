import { useState, useCallback } from "react";
import { format } from "date-fns";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { events as eventsApi, calendars } from "@/api/endpoints";
import { useHouseholdStore } from "@/stores/householdStore";

interface QuickAddEventProps {
  onClose: () => void;
  defaultDate?: Date;
}

export default function QuickAddEvent({
  onClose,
  defaultDate = new Date(),
}: QuickAddEventProps) {
  const queryClient = useQueryClient();
  const householdId = useHouseholdStore((s) => s.householdId);
  const profiles = useHouseholdStore((s) => s.profiles);
  const todayStr = format(defaultDate, "yyyy-MM-dd");

  const [title, setTitle] = useState("");
  const [date, setDate] = useState(todayStr);
  const [startTime, setStartTime] = useState("09:00");
  const [endTime, setEndTime] = useState("10:00");
  const [profileId, setProfileId] = useState(profiles[0]?.id ?? "");

  const { data: calendarList = [], isLoading: calendarsLoading } = useQuery({
    queryKey: ["calendars", householdId],
    queryFn: async () => {
      const res = await calendars.getAll(householdId!);
      return res.data as { id: string; name: string }[];
    },
    enabled: !!householdId,
  });

  const sourceCalendarId = calendarList[0]?.id;

  const createMutation = useMutation({
    mutationFn: async () => {
      await eventsApi.create({
        title,
        start_time: `${date}T${startTime}`,
        end_time: `${date}T${endTime}`,
        profile_id: profileId || undefined,
        source_calendar_id: sourceCalendarId!,
        all_day: false,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["events"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      onClose();
    },
  });

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!title.trim() || !sourceCalendarId) return;
      createMutation.mutate();
    },
    [title, sourceCalendarId, createMutation],
  );

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/50 p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
    >
      <form
        className="w-full max-w-md rounded-2xl bg-white dark:bg-gray-800 shadow-xl p-6 space-y-4"
        onClick={(e) => e.stopPropagation()}
        onSubmit={handleSubmit}
      >
        <h2 className="text-lg font-bold">Quick Add Event</h2>

        {!calendarsLoading && !sourceCalendarId && (
          <p className="text-sm text-amber-600 dark:text-amber-400">
            Create a calendar first before adding events.
          </p>
        )}

        <input
          type="text"
          placeholder="Event title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          autoFocus
          className="block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent px-4 py-3 text-lg min-h-[44px]"
        />

        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent px-4 py-3 text-base min-h-[44px]"
        />

        <div className="grid grid-cols-2 gap-3">
          <label className="block">
            <span className="text-sm text-gray-500 dark:text-gray-400">Start</span>
            <input
              type="time"
              value={startTime}
              onChange={(e) => setStartTime(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent px-4 py-3 text-base min-h-[44px]"
            />
          </label>
          <label className="block">
            <span className="text-sm text-gray-500 dark:text-gray-400">End</span>
            <input
              type="time"
              value={endTime}
              onChange={(e) => setEndTime(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent px-4 py-3 text-base min-h-[44px]"
            />
          </label>
        </div>

        {profiles.length > 0 && (
          <select
            value={profileId}
            onChange={(e) => setProfileId(e.target.value)}
            className="block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent px-4 py-3 text-base min-h-[44px]"
          >
            <option value="">Select profile</option>
            {profiles.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        )}

        <div className="flex gap-3 pt-2">
          <button
            type="submit"
            disabled={createMutation.isPending || !title.trim() || !sourceCalendarId}
            className="min-h-[44px] flex-1 rounded-lg bg-blue-600 text-white font-medium px-4 py-3 hover:bg-blue-700 disabled:opacity-50"
          >
            {createMutation.isPending ? "Adding…" : "Add Event"}
          </button>
          <button
            type="button"
            onClick={onClose}
            className="min-h-[44px] flex-1 rounded-lg border border-gray-300 dark:border-gray-600 font-medium px-4 py-3 hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            Cancel
          </button>
        </div>

        {createMutation.isError && (
          <p className="text-sm text-red-600 dark:text-red-400">
            Failed to create event. Please try again.
          </p>
        )}
      </form>
    </div>
  );
}
