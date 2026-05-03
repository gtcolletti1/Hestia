import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  format,
  startOfMonth,
  endOfMonth,
  startOfWeek,
  endOfWeek,
  addDays,
  isSameMonth,
  isToday,
} from "date-fns";
import { events as eventsApi } from "@/api/endpoints";
import { useHouseholdStore } from "@/stores/householdStore";
import type { CalendarEvent } from "./types";
import { mapEventToCalendarEvent, eventOccursOnDay } from "./types";

interface MonthViewProps {
  date: Date;
  onSelectDay?: (day: Date) => void;
}

const MAX_VISIBLE_EVENTS = 3;
const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export default function MonthView({ date, onSelectDay }: MonthViewProps) {
  const monthStart = startOfMonth(date);
  const monthEnd = endOfMonth(date);
  const calStart = startOfWeek(monthStart, { weekStartsOn: 0 });
  const calEnd = endOfWeek(monthEnd, { weekStartsOn: 0 });

  const householdId = useHouseholdStore((s) => s.householdId);
  const profiles = useHouseholdStore((s) => s.profiles);

  const [hoveredDay, setHoveredDay] = useState<string | null>(null);

  const { data: rawEvents = [] } = useQuery({
    queryKey: ["events", "month", format(monthStart, "yyyy-MM"), householdId],
    queryFn: async () => {
      const res = await eventsApi.getAll(householdId!, {
        start_date: format(calStart, "yyyy-MM-dd"),
        end_date: format(calEnd, "yyyy-MM-dd"),
      });
      return res.data;
    },
    enabled: !!householdId,
  });

  const events = rawEvents.map((ev) => mapEventToCalendarEvent(ev, profiles));

  // Build array of weeks → days
  const weeks: Date[][] = [];
  let cursor = calStart;
  while (cursor <= calEnd) {
    const week: Date[] = [];
    for (let i = 0; i < 7; i++) {
      week.push(cursor);
      cursor = addDays(cursor, 1);
    }
    weeks.push(week);
  }

  function eventsForDay(day: Date): CalendarEvent[] {
    return events.filter((e) => eventOccursOnDay(e, day));
  }

  return (
    <div>
      {/* Day name headers */}
      <div className="grid grid-cols-7 text-center text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
        {DAY_NAMES.map((d) => (
          <div key={d} className="py-2">
            {d}
          </div>
        ))}
      </div>

      {/* Weeks */}
      <div className="grid grid-cols-7 border-t border-l border-gray-200 dark:border-gray-700">
        {weeks.flat().map((day) => {
          const dayKey = format(day, "yyyy-MM-dd");
          const dayEvts = eventsForDay(day);
          const isCurrentMonth = isSameMonth(day, date);
          const isCurrentDay = isToday(day);

          return (
            <button
              key={dayKey}
              onClick={() => onSelectDay?.(day)}
              onMouseEnter={() => setHoveredDay(dayKey)}
              onMouseLeave={() => setHoveredDay(null)}
              className={`
                relative min-h-[80px] border-r border-b border-gray-200 dark:border-gray-700
                p-1 text-left transition-colors
                ${isCurrentMonth ? "" : "opacity-40"}
                ${hoveredDay === dayKey ? "bg-gray-50 dark:bg-gray-800" : ""}
              `}
            >
              <span
                className={`
                  inline-flex h-7 w-7 items-center justify-center rounded-full text-sm font-medium
                  ${isCurrentDay ? "bg-blue-600 text-white ring-2 ring-blue-300" : ""}
                `}
              >
                {format(day, "d")}
              </span>

              {/* Event pills */}
              <div className="mt-0.5 space-y-0.5 overflow-hidden">
                {dayEvts.slice(0, MAX_VISIBLE_EVENTS).map((ev) => (
                  <div
                    key={ev.id}
                    className="flex items-center gap-1 min-h-[18px]"
                  >
                    <span
                      className="h-2 w-2 shrink-0 rounded-full"
                      style={{ backgroundColor: ev.profile_color || "#3b82f6" }}
                    />
                    <span className="text-xs truncate">{ev.title}</span>
                  </div>
                ))}
                {dayEvts.length > MAX_VISIBLE_EVENTS && (
                  <span className="text-xs text-gray-400 dark:text-gray-500">
                    +{dayEvts.length - MAX_VISIBLE_EVENTS} more
                  </span>
                )}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
