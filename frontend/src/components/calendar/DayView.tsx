import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  format,
  parseISO,
  startOfDay,
  addHours,
  differenceInMinutes,
} from "date-fns";
import { events as eventsApi } from "@/api/endpoints";
import { useHouseholdStore } from "@/stores/householdStore";
import type { CalendarEvent } from "./types";
import { mapEventToCalendarEvent } from "./types";
import EventModal from "./EventModal";
import QuickAddEvent from "./QuickAddEvent";

interface DayViewProps {
  date: Date;
}

const START_HOUR = 6;
const END_HOUR = 22;
const HOUR_HEIGHT_PX = 72;
const TOTAL_HOURS = END_HOUR - START_HOUR;

export default function DayView({ date }: DayViewProps) {
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);
  const [showQuickAdd, setShowQuickAdd] = useState(false);

  const householdId = useHouseholdStore((s) => s.householdId);
  const profiles = useHouseholdStore((s) => s.profiles);

  const dayStart = format(date, "yyyy-MM-dd");

  const { data: rawEvents = [], isLoading } = useQuery({
    queryKey: ["events", "day", dayStart, householdId],
    queryFn: async () => {
      const res = await eventsApi.getAll(householdId!, {
        start_date: dayStart,
        end_date: dayStart,
      });
      return res.data;
    },
    enabled: !!householdId,
  });

  const dayEvents = rawEvents.map((ev) => mapEventToCalendarEvent(ev, profiles));

  const hours = Array.from({ length: TOTAL_HOURS }, (_, i) => START_HOUR + i);

  function getEventStyle(ev: CalendarEvent) {
    const start = parseISO(ev.start);
    const end = parseISO(ev.end);
    const dayOrigin = addHours(startOfDay(date), START_HOUR);
    const topMin = Math.max(0, differenceInMinutes(start, dayOrigin));
    const durationMin = Math.max(15, differenceInMinutes(end, start));

    const top = (topMin / 60) * HOUR_HEIGHT_PX;
    const height = Math.min(
      (durationMin / 60) * HOUR_HEIGHT_PX,
      TOTAL_HOURS * HOUR_HEIGHT_PX - top,
    );

    return { top: `${top}px`, height: `${height}px` };
  }

  return (
    <div className="relative">
      {/* Time grid */}
      <div className="relative" style={{ height: `${TOTAL_HOURS * HOUR_HEIGHT_PX}px` }}>
        {hours.map((h) => {
          const label = format(addHours(startOfDay(date), h), "h a");
          const top = (h - START_HOUR) * HOUR_HEIGHT_PX;
          return (
            <div
              key={h}
              className="absolute left-0 right-0 border-t border-gray-200 dark:border-gray-700"
              style={{ top: `${top}px`, height: `${HOUR_HEIGHT_PX}px` }}
            >
              <span className="absolute -top-2.5 left-2 text-xs text-gray-400 dark:text-gray-500 select-none">
                {label}
              </span>
            </div>
          );
        })}

        {/* Events */}
        {isLoading ? (
          <div className="ml-16 space-y-2 pt-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div
                key={i}
                className="animate-pulse h-14 rounded-lg bg-gray-200 dark:bg-gray-700"
              />
            ))}
          </div>
        ) : (
          dayEvents.map((ev) => (
            <button
              key={ev.id}
              onClick={() => setSelectedEvent(ev)}
              className="absolute left-16 right-4 rounded-lg px-3 py-1 text-left text-sm text-white shadow-sm overflow-hidden cursor-pointer min-h-[44px] hover:opacity-90 transition-opacity"
              style={{
                ...getEventStyle(ev),
                backgroundColor: ev.profile_color || "#3b82f6",
              }}
            >
              <p className="font-medium truncate">{ev.title}</p>
              <p className="text-xs opacity-90">
                {format(parseISO(ev.start), "h:mm a")}
              </p>
              <span className="inline-block mt-0.5 text-xs bg-white/20 rounded px-1">
                {ev.profile_name}
              </span>
            </button>
          ))
        )}
      </div>

      {/* FAB */}
      <button
        onClick={() => setShowQuickAdd(true)}
        className="fixed bottom-8 right-8 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-blue-600 text-white text-2xl shadow-lg hover:bg-blue-700 active:scale-95 transition-transform"
        aria-label="Add event"
      >
        +
      </button>

      {selectedEvent && (
        <EventModal event={selectedEvent} onClose={() => setSelectedEvent(null)} profiles={profiles} />
      )}
      {showQuickAdd && (
        <QuickAddEvent onClose={() => setShowQuickAdd(false)} defaultDate={date} />
      )}
    </div>
  );
}
