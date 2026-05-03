import { useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  format,
  parseISO,
  addDays,
  startOfDay,
  endOfDay,
  isToday,
  isTomorrow,
  differenceInCalendarDays,
} from "date-fns";
import { formatTime } from "@/utils/timeFormat";
import { events as eventsApi } from "@/api/endpoints";
import { useHouseholdStore } from "@/stores/householdStore";
import { useHouseholdSettings } from "@/hooks/useHouseholdSettings";
import type { CalendarEvent } from "./types";
import { mapEventToCalendarEvent } from "./types";
import EventModal from "./EventModal";

interface AgendaViewProps {
  date: Date;
}

const PAGE_DAYS = 14;

export default function AgendaView({ date }: AgendaViewProps) {
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);
  const [daysToShow, setDaysToShow] = useState(PAGE_DAYS);

  const rangeEnd = addDays(date, daysToShow);

  const householdId = useHouseholdStore((s) => s.householdId);
  const storeProfiles = useHouseholdStore((s) => s.profiles);
  const { timeFormat } = useHouseholdSettings();

  const { data: rawEvents = [], isLoading } = useQuery({
    queryKey: ["events", "agenda", format(date, "yyyy-MM-dd"), daysToShow, householdId],
    queryFn: async () => {
      const res = await eventsApi.getAll(householdId!, {
        start_date: format(date, "yyyy-MM-dd"),
        end_date: format(rangeEnd, "yyyy-MM-dd"),
      });
      return res.data;
    },
    enabled: !!householdId,
  });

  const events = rawEvents.map((ev) => mapEventToCalendarEvent(ev, storeProfiles));

  // Group events by every day they overlap within the visible window.
  // A multi-day event appears under each of its days with a "Day X of Y" badge.
  const windowStart = startOfDay(date);
  const windowEnd = endOfDay(rangeEnd);
  type AgendaItem = { ev: CalendarEvent; dayIndex: number; totalDays: number };
  const grouped: Record<string, AgendaItem[]> = {};

  for (const ev of events) {
    const evStart = parseISO(ev.start);
    const evEnd = parseISO(ev.end);
    // First day visible to the user
    const firstDay = evStart < windowStart ? windowStart : startOfDay(evStart);
    // Last day this event occupies. iCal all-day end is exclusive (midnight of
    // the day after), so subtract 1ms before taking startOfDay.
    const lastDay = startOfDay(new Date(evEnd.getTime() - 1));
    const visibleLastDay = lastDay > windowEnd ? windowEnd : lastDay;
    if (visibleLastDay < firstDay) continue;

    const totalDays = differenceInCalendarDays(lastDay, startOfDay(evStart)) + 1;
    let cursor = firstDay;
    while (cursor <= visibleLastDay) {
      const key = format(cursor, "yyyy-MM-dd");
      const dayIndex = differenceInCalendarDays(cursor, startOfDay(evStart)) + 1;
      if (!grouped[key]) grouped[key] = [];
      grouped[key].push({ ev, dayIndex, totalDays });
      cursor = addDays(cursor, 1);
    }
  }

  // Sort date keys
  const sortedDates = Object.keys(grouped).sort();

  const loadMore = useCallback(() => {
    setDaysToShow((prev) => prev + PAGE_DAYS);
  }, []);

  function dayLabel(dateStr: string): string {
    const d = parseISO(dateStr);
    if (isToday(d)) return "Today";
    if (isTomorrow(d)) return "Tomorrow";
    return format(d, "EEEE");
  }

  return (
    <div className="space-y-6">
      {isLoading && (
        <div className="space-y-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div
              key={i}
              className="animate-pulse h-16 rounded-lg bg-gray-200 dark:bg-gray-700"
            />
          ))}
        </div>
      )}

      {!isLoading && sortedDates.length === 0 && (
        <p className="text-center text-gray-400 dark:text-gray-500 py-12">
          No upcoming events
        </p>
      )}

      {sortedDates.map((dateKey) => (
        <section key={dateKey}>
          <h3 className="sticky top-0 z-10 bg-gray-50 dark:bg-gray-900 py-2 text-sm font-semibold text-gray-600 dark:text-gray-300 border-b border-gray-200 dark:border-gray-700">
            {dayLabel(dateKey)} · {format(parseISO(dateKey), "MMM d, yyyy")}
          </h3>

          <ul className="divide-y divide-gray-100 dark:divide-gray-800">
            {grouped[dateKey]
              .sort((a, b) => a.ev.start.localeCompare(b.ev.start))
              .map(({ ev, dayIndex, totalDays }) => (
                <li key={`${ev.id}-${dayIndex}`}>
                  <button
                    onClick={() => setSelectedEvent(ev)}
                    className="flex items-start gap-3 w-full text-left px-2 py-3 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors min-h-[56px]"
                  >
                    <span
                      className="mt-1.5 h-3 w-3 shrink-0 rounded-full"
                      style={{ backgroundColor: ev.profile_color || "#3b82f6" }}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">
                        {ev.recurrence_rule && <span title="Recurring">🔁 </span>}
                        {ev.title}
                        {totalDays > 1 && (
                          <span className="ml-2 text-xs font-normal text-gray-400 dark:text-gray-500">
                            (day {dayIndex} of {totalDays})
                          </span>
                        )}
                      </p>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        {ev.all_day || totalDays > 1
                          ? "All day"
                          : `${formatTime(parseISO(ev.start), "h:mm a", timeFormat)} – ${formatTime(parseISO(ev.end), "h:mm a", timeFormat)}`}
                      </p>
                      {ev.location && (
                        <p className="text-sm text-gray-400 dark:text-gray-500 truncate">
                          📍 {ev.location}
                        </p>
                      )}
                    </div>
                    <span className="shrink-0 mt-1 text-xs bg-gray-100 dark:bg-gray-700 rounded-full px-2 py-0.5">
                      {ev.profile_name}
                    </span>
                  </button>
                </li>
              ))}
          </ul>
        </section>
      ))}

      {!isLoading && sortedDates.length > 0 && (
        <div className="text-center pt-2 pb-6">
          <button
            onClick={loadMore}
            className="min-h-[44px] rounded-lg border border-gray-300 dark:border-gray-600 px-6 py-2 text-sm font-medium hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          >
            Load more
          </button>
        </div>
      )}

      {selectedEvent && (
        <EventModal event={selectedEvent} onClose={() => setSelectedEvent(null)} profiles={storeProfiles} />
      )}
    </div>
  );
}
