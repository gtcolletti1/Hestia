import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  format,
  parseISO,
  startOfDay,
  endOfDay,
  addHours,
  differenceInMinutes,
} from "date-fns";
import { formatTime } from "@/utils/timeFormat";
import { events as eventsApi } from "@/api/endpoints";
import { useHouseholdStore } from "@/stores/householdStore";
import { useHouseholdSettings } from "@/hooks/useHouseholdSettings";
import type { CalendarEvent } from "./types";
import { mapEventToCalendarEvent, isMultiDay } from "./types";
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
  const { timeFormat } = useHouseholdSettings();

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

  const allEvents = rawEvents.map((ev) => mapEventToCalendarEvent(ev, profiles));
  const bannerEvents = allEvents.filter((e) => e.all_day || isMultiDay(e));
  const dayEvents = allEvents.filter((e) => !e.all_day && !isMultiDay(e));

  const hours = Array.from({ length: TOTAL_HOURS }, (_, i) => START_HOUR + i);

  function getEventStyle(ev: CalendarEvent) {
    const start = parseISO(ev.start);
    const end = parseISO(ev.end);
    const dayOrigin = addHours(startOfDay(date), START_HOUR);
    const dayEndBoundary = endOfDay(date);
    // Clip to today for multi-day events.
    const visibleStart = start < dayOrigin ? dayOrigin : start;
    const visibleEnd = end > dayEndBoundary ? dayEndBoundary : end;
    const topMin = Math.max(0, differenceInMinutes(visibleStart, dayOrigin));
    const durationMin = Math.max(15, differenceInMinutes(visibleEnd, visibleStart));

    const top = (topMin / 60) * HOUR_HEIGHT_PX;
    const height = Math.min(
      (durationMin / 60) * HOUR_HEIGHT_PX,
      TOTAL_HOURS * HOUR_HEIGHT_PX - top,
    );

    return { top: `${top}px`, height: `${height}px` };
  }

  function continuationLabel(ev: CalendarEvent): string {
    const start = parseISO(ev.start);
    const end = parseISO(ev.end);
    const before = start < startOfDay(date);
    const after = end > endOfDay(date);
    if (before && after) return `↔ ${ev.title}`;
    if (before) return `← ${ev.title}`;
    if (after) return `${ev.title} →`;
    return ev.title;
  }

  return (
    <div className="relative">
      {/* All-day / multi-day banner */}
      {bannerEvents.length > 0 && (
        <div className="mb-2 flex items-start gap-2 border-b border-gray-200 dark:border-gray-700 pb-2">
          <span className="text-[10px] uppercase tracking-wide text-gray-400 dark:text-gray-500 pt-1 w-12 text-right shrink-0">
            all-day
          </span>
          <div className="flex flex-wrap gap-1 flex-1">
            {bannerEvents.map((ev) => (
              <button
                key={ev.id}
                onClick={() => setSelectedEvent(ev)}
                className="rounded px-2 py-1 text-sm text-white text-left cursor-pointer hover:opacity-90 transition-opacity"
                style={{ backgroundColor: ev.profile_color || "#3b82f6" }}
              >
                {ev.recurrence_rule && <span title="Recurring">🔁 </span>}
                <span className="privacy-blur">{continuationLabel(ev)}</span>
                <span className="ml-2 text-xs opacity-90 privacy-blur">{ev.profile_name}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Time grid */}
      <div className="relative" style={{ height: `${TOTAL_HOURS * HOUR_HEIGHT_PX}px` }}>
        {hours.map((h) => {
          const label = formatTime(addHours(startOfDay(date), h), "h a", timeFormat);
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
              <p className="font-medium truncate">
                {ev.recurrence_rule && <span title="Recurring">🔁 </span>}
                <span className="privacy-blur">{continuationLabel(ev)}</span>
              </p>
              <p className="text-xs opacity-90">
                {formatTime(parseISO(ev.start), "h:mm a", timeFormat)}
              </p>
              <span className="inline-block mt-0.5 text-xs bg-white/20 rounded px-1 privacy-blur">
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
