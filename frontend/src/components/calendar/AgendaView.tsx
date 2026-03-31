import { useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  format,
  parseISO,
  addDays,
  isToday,
  isTomorrow,
} from "date-fns";
import client from "@/api/client";
import type { CalendarEvent } from "./types";
import EventModal from "./EventModal";

interface AgendaViewProps {
  date: Date;
}

const PAGE_DAYS = 14;

export default function AgendaView({ date }: AgendaViewProps) {
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);
  const [daysToShow, setDaysToShow] = useState(PAGE_DAYS);

  const rangeEnd = addDays(date, daysToShow);

  const { data: events = [], isLoading } = useQuery<CalendarEvent[]>({
    queryKey: ["events", "agenda", format(date, "yyyy-MM-dd"), daysToShow],
    queryFn: async () => {
      const res = await client.get<CalendarEvent[]>("/events", {
        params: {
          start: format(date, "yyyy-MM-dd'T'00:00:00"),
          end: format(rangeEnd, "yyyy-MM-dd'T'23:59:59"),
        },
      });
      return res.data;
    },
  });

  // Group events by date
  const grouped = events.reduce<Record<string, CalendarEvent[]>>((acc, ev) => {
    const key = format(parseISO(ev.start), "yyyy-MM-dd");
    if (!acc[key]) acc[key] = [];
    acc[key].push(ev);
    return acc;
  }, {});

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
              .sort((a, b) => a.start.localeCompare(b.start))
              .map((ev) => (
                <li key={ev.id}>
                  <button
                    onClick={() => setSelectedEvent(ev)}
                    className="flex items-start gap-3 w-full text-left px-2 py-3 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors min-h-[56px]"
                  >
                    <span
                      className="mt-1.5 h-3 w-3 shrink-0 rounded-full"
                      style={{ backgroundColor: ev.profile_color || "#3b82f6" }}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{ev.title}</p>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        {format(parseISO(ev.start), "h:mm a")}
                        {" – "}
                        {format(parseISO(ev.end), "h:mm a")}
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
        <EventModal event={selectedEvent} onClose={() => setSelectedEvent(null)} />
      )}
    </div>
  );
}
