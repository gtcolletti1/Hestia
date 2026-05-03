import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  format,
  parseISO,
  startOfWeek,
  addDays,
  addHours,
  startOfDay,
  endOfDay,
  differenceInMinutes,
  isToday,
} from "date-fns";
import { formatTime } from "@/utils/timeFormat";
import { events as eventsApi } from "@/api/endpoints";
import { useHouseholdStore } from "@/stores/householdStore";
import { useHouseholdSettings } from "@/hooks/useHouseholdSettings";
import type { CalendarEvent } from "./types";
import { mapEventToCalendarEvent, eventOccursOnDay, isMultiDay } from "./types";
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
  const { timeFormat } = useHouseholdSettings();

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

  // Split into banner (all-day or multi-day) vs timed events.
  const bannerEvents = events.filter((e) => e.all_day || isMultiDay(e));
  const timedEvents = events.filter((e) => !e.all_day && !isMultiDay(e));

  // Compute the column span (1-based, into the 7-col day grid) for each
  // banner event within the visible week, then assign rows greedily so they
  // don't visually overlap.
  type BannerLayout = {
    ev: CalendarEvent;
    startCol: number; // 1..7
    endCol: number; // 1..7 inclusive
    row: number; // 0-based
  };
  const weekStartDay = startOfDay(weekStart);
  const weekEndDay = startOfDay(addDays(weekStart, 6));
  const layouts: BannerLayout[] = [];
  const rowEnds: number[] = []; // last endCol per row

  const sortedBanners = [...bannerEvents].sort((a, b) =>
    a.start.localeCompare(b.start),
  );
  for (const ev of sortedBanners) {
    const evStart = parseISO(ev.start);
    const evEndExclusive = parseISO(ev.end);
    // Last day occupied (treat exclusive end -1ms).
    const evLastDay = startOfDay(new Date(evEndExclusive.getTime() - 1));
    const visibleStartDay = evStart < weekStart ? weekStartDay : startOfDay(evStart);
    const visibleEndDay = evLastDay > weekEndDay ? weekEndDay : evLastDay;
    if (visibleEndDay < weekStartDay || visibleStartDay > weekEndDay) continue;
    const startCol =
      Math.round(
        (visibleStartDay.getTime() - weekStartDay.getTime()) / 86400000,
      ) + 1;
    const endCol =
      Math.round(
        (visibleEndDay.getTime() - weekStartDay.getTime()) / 86400000,
      ) + 1;
    let row = rowEnds.findIndex((end) => end < startCol);
    if (row === -1) {
      row = rowEnds.length;
      rowEnds.push(endCol);
    } else {
      rowEnds[row] = endCol;
    }
    layouts.push({ ev, startCol, endCol, row });
  }
  const bannerRowCount = rowEnds.length;

  function getEventStyle(ev: CalendarEvent, day: Date) {
    const start = parseISO(ev.start);
    const end = parseISO(ev.end);
    const dayOrigin = addHours(startOfDay(day), START_HOUR);
    const dayEndBoundary = endOfDay(day);
    // Clip the rendered slice to *this* day for multi-day events.
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

  function continuationLabel(ev: CalendarEvent, day: Date): string {
    const start = parseISO(ev.start);
    const end = parseISO(ev.end);
    const before = start < startOfDay(day);
    const after = end > endOfDay(day);
    if (before && after) return `↔ ${ev.title}`;
    if (before) return `← ${ev.title}`;
    if (after) return `${ev.title} →`;
    return ev.title;
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

      {/* All-day / multi-day banner row */}
      {bannerRowCount > 0 && (
        <div className="grid grid-cols-[56px_repeat(7,1fr)] border-b border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-800/30">
          <div className="text-[10px] uppercase tracking-wide text-gray-400 dark:text-gray-500 px-1 py-1 text-right pr-2">
            all-day
          </div>
          <div
            className="col-span-7 grid grid-cols-7 gap-y-0.5 py-1 px-0.5"
            style={{ gridTemplateRows: `repeat(${bannerRowCount}, minmax(22px, auto))` }}
          >
            {layouts.map(({ ev, startCol, endCol, row }) => (
              <button
                key={`${ev.id}-${row}`}
                onClick={() => setSelectedEvent(ev)}
                className="rounded px-1.5 py-0.5 text-xs text-white truncate text-left cursor-pointer hover:opacity-90 transition-opacity mx-0.5"
                style={{
                  gridColumnStart: startCol,
                  gridColumnEnd: endCol + 1,
                  gridRowStart: row + 1,
                  backgroundColor: ev.profile_color || "#3b82f6",
                }}
                title={ev.title}
              >
                {ev.recurrence_rule ? "🔁 " : ""}
                <span className="">{ev.title}</span>
              </button>
            ))}
          </div>
        </div>
      )}

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
                {formatTime(addHours(startOfDay(date), h), "h a", timeFormat)}
              </span>
            </div>
          ))}
        </div>

        {days.map((d) => {
          const dayEvents = timedEvents.filter((e) => eventOccursOnDay(e, d));
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
                    {ev.recurrence_rule ? "🔁 " : ""}
                    <span className="">{continuationLabel(ev, d)}</span>
                  </button>
                ))}
            </div>
          );
        })}
      </div>

      {selectedEvent && (
        <EventModal event={selectedEvent} onClose={() => setSelectedEvent(null)} profiles={storeProfiles} />
      )}
    </div>
  );
}
