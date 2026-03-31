import { useState, useCallback } from "react";
import {
  format,
  addDays,
  subDays,
  addWeeks,
  subWeeks,
  addMonths,
  subMonths,
  startOfWeek,
  endOfWeek,
} from "date-fns";
import type { CalendarViewMode } from "./types";
import DayView from "./DayView";
import WeekView from "./WeekView";
import MonthView from "./MonthView";
import AgendaView from "./AgendaView";

const VIEW_LABELS: { key: CalendarViewMode; label: string }[] = [
  { key: "day", label: "Day" },
  { key: "week", label: "Week" },
  { key: "month", label: "Month" },
  { key: "agenda", label: "Agenda" },
];

export default function CalendarView() {
  const [view, setView] = useState<CalendarViewMode>("week");
  const [currentDate, setCurrentDate] = useState(new Date());

  const goToday = useCallback(() => setCurrentDate(new Date()), []);

  const goPrev = useCallback(() => {
    setCurrentDate((d) => {
      switch (view) {
        case "day":
          return subDays(d, 1);
        case "week":
          return subWeeks(d, 1);
        case "month":
          return subMonths(d, 1);
        case "agenda":
          return subDays(d, 14);
      }
    });
  }, [view]);

  const goNext = useCallback(() => {
    setCurrentDate((d) => {
      switch (view) {
        case "day":
          return addDays(d, 1);
        case "week":
          return addWeeks(d, 1);
        case "month":
          return addMonths(d, 1);
        case "agenda":
          return addDays(d, 14);
      }
    });
  }, [view]);

  function handleMonthDaySelect(day: Date) {
    setCurrentDate(day);
    setView("day");
  }

  function getHeading(): string {
    switch (view) {
      case "day":
        return format(currentDate, "EEEE, MMMM d, yyyy");
      case "week": {
        const ws = startOfWeek(currentDate, { weekStartsOn: 0 });
        const we = endOfWeek(currentDate, { weekStartsOn: 0 });
        return `${format(ws, "MMM d")} – ${format(we, "MMM d, yyyy")}`;
      }
      case "month":
        return format(currentDate, "MMMM yyyy");
      case "agenda":
        return `Starting ${format(currentDate, "MMM d, yyyy")}`;
    }
  }

  return (
    <div className="space-y-4">
      {/* Navigation bar */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Prev / Today / Next */}
        <div className="flex items-center gap-1">
          <button
            onClick={goPrev}
            className="min-h-[44px] min-w-[44px] flex items-center justify-center rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700"
            aria-label="Previous"
          >
            ‹
          </button>
          <button
            onClick={goToday}
            className="min-h-[44px] rounded-lg border border-gray-300 dark:border-gray-600 px-4 font-medium text-sm hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            Today
          </button>
          <button
            onClick={goNext}
            className="min-h-[44px] min-w-[44px] flex items-center justify-center rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700"
            aria-label="Next"
          >
            ›
          </button>
        </div>

        {/* Date heading */}
        <h2 className="text-lg font-semibold flex-1 min-w-0 truncate">
          {getHeading()}
        </h2>

        {/* View switcher */}
        <div className="flex rounded-lg border border-gray-300 dark:border-gray-600 overflow-hidden">
          {VIEW_LABELS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setView(key)}
              className={`min-h-[44px] px-4 text-sm font-medium transition-colors ${
                view === key
                  ? "bg-blue-600 text-white"
                  : "hover:bg-gray-100 dark:hover:bg-gray-700"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* View content */}
      <div>
        {view === "day" && <DayView date={currentDate} />}
        {view === "week" && <WeekView date={currentDate} />}
        {view === "month" && (
          <MonthView date={currentDate} onSelectDay={handleMonthDaySelect} />
        )}
        {view === "agenda" && <AgendaView date={currentDate} />}
      </div>
    </div>
  );
}
