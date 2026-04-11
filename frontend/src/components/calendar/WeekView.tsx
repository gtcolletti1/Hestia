import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  format,
  parseISO,
  startOfWeek,
  addDays,
  addHours,
  startOfDay,
  differenceInMinutes,
  isSameDay,
  isToday,
} from "date-fns";
import { events as eventsApi } from "@/api/endpoints";
import { useHouseholdStore } from "@/stores/householdStore";
import type { CalendarEvent } from "./types";
import { mapEventToCalendarEvent } from "./types";
import EventModal from "./EventModal";

interface WeekViewProps {
  date: Date;
}

const START_HOUR = 6;
const END_HOUR = 22;
const HOUR_HEIGHT_PX = 56;
const TOTAL_HOURS = END_HOUR - START_HOUR;

export default function WeekView({ date }: WeekViewProps) {
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);
  const weekStart = startOfWeek(date, { weekStartsOn: 0 });
  const weekEnd = addDays(weekStart, 6);

  const householdId = useHouseholdStore((s) => s.householdId);
  const storeProfiles = useHouseholdStore((s) => s.profiles);

  const { data: rawEvents = [], isLoading } = useQuery({
    queryKey: ["events", "week", format(weekStart, "yyyy-MM-dd"), householdId],
    queryFn: async () => {
      const res = await eventsApi.getAll(householdId!, {
        start_date: format(weekStart, "yyyy-MM-dd"),
        end_date: format(weekEnd, "yyyy-MM-dd"),
      });
      return res.data;
    },
    enabled: !!householdId,
  });

  const events = rawEvents.map((ev) => mapEventToCalendarEvent(ev, storeProfiles));

  const days = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));
  const hours = Array.from({ length: TOTAL_HOURS }, (_, i) => START_HOUR + i);

  function getEventStyle(ev: CalendarEvent, day: Date) {
    const start = parseISO(ev.start);
    const end = parseISO(ev.end);
    const dayOrigin = addHours(startOfDay(day), START_HOUR);
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
    <div className="overflow-x-auto">
      {/* Day headers */}
      <div className="grid grid-cols-[56px_repeat(7,1fr)] sticky top-0 bg-white dark:bg-gray-900 z-10">
        <div />
        {days.map((d) => (
          <div
            key={d.toISOString()}
            className={`text-center py-2 text-sm font-medium border-b border-gray-200 dark:border-gray-700 ${
              isToday(d) ? "text-blue-600 dark:text-blue-400" : "text-gray-600 dark:text-gray-300"
            }`}
          >
            <span className="block text-xs text-gray-400">{format(d, "EEE")}</span>
            <span
              className={`inline-flex h-8 w-8 items-center justify-center rounded-full ${
                isToday(d) ? "bg-blue-600 text-white" : ""
              }`}
            >
              {format(d, "d")}
            </span>
          </div>
        ))}
      </div>

      {/* Grid body */}
      <div className="grid grid-cols-[56px_repeat(7,1fr)]">
        {/* Time labels column + 7 day columns */}
        <div className="relative" style={{ height: `${TOTAL_HOURS * HOUR_HEIGHT_PX}px` }}>
          {hours.map((h) => (
            <div
              key={h}
              className="absolute left-0 right-0"
              style={{ top: `${(h - START_HOUR) * HOUR_HEIGHT_PX}px` }}
            >
              <span className="text-xs text-gray-400 dark:text-gray-500 pl-1 select-none">
                {format(addHours(startOfDay(date), h), "h a")}
              </span>
            </div>
          ))}
        </div>

        {days.map((d) => {
          const dayEvents = events.filter((e) => isSameDay(parseISO(e.start), d));
          return (
            <div
              key={d.toISOString()}
              className={`relative border-l border-gray-200 dark:border-gray-700 ${
                isToday(d) ? "bg-blue-50/50 dark:bg-blue-900/10" : ""
              }`}
              style={{ height: `${TOTAL_HOURS * HOUR_HEIGHT_PX}px` }}
            >
              {/* Hour grid lines */}
              {hours.map((h) => (
                <div
                  key={h}
                  className="absolute left-0 right-0 border-t border-gray-100 dark:border-gray-800"
                  style={{ top: `${(h - START_HOUR) * HOUR_HEIGHT_PX}px` }}
                />
              ))}

              {/* Events */}
              {!isLoading &&
                dayEvents.map((ev) => (
                  <button
                    key={ev.id}
                    onClick={() => setSelectedEvent(ev)}
                    className="absolute left-0.5 right-0.5 rounded px-1 py-0.5 text-xs text-white truncate cursor-pointer min-h-[22px] hover:opacity-90 transition-opacity"
                    style={{
                      ...getEventStyle(ev, d),
                      backgroundColor: ev.profile_color || "#3b82f6",
                    }}
                  >
                    {ev.title}
                  </button>
                ))}
            </div>
          );
        })}
      </div>

      {selectedEvent && (
        <EventModal event={selectedEvent} onClose={() => setSelectedEvent(null)} />
      )}
    </div>
  );
}
