import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { format, parseISO } from "date-fns";
import { formatTime } from "@/utils/timeFormat";
import { KID_SAFE_PALETTE, TIME_BLOCK_COLOR } from "./palette";
import type {
  SplashDay,
  SplashEvent,
  SplashMeal,
  SplashMessage,
  SplashResponse,
  SplashRoutine,
  SplashWeather,
} from "@/types/splash";

interface SplashContentProps {
  data: SplashResponse;
  timeFormat: "12h" | "24h";
}

/**
 * The "ambient" content layer: clock + adaptive grid of policy-allowed
 * sections (agenda, routines, meals, weather, messages).
 *
 * Layout philosophy:
 * - Single visual frame; no scrolling.
 * - Clock is always present and visually dominant.
 * - All other sections are best-effort: each is rendered only if the
 *   server returned a non-null block (i.e. the admin policy permits it
 *   and there's content to show).
 * - The agenda block self-trims to fit the viewport (see ``AgendaBlock``).
 */
export default function SplashContent({ data, timeFormat }: SplashContentProps) {
  const { clock, days, routines, meals, weather, messages, vacation } = data;

  const hasAgenda = days !== null && days.length > 0;
  const hasRoutines = routines !== null && routines.length > 0;
  const hasMeals = meals !== null && meals.length > 0;
  const hasWeather = weather !== null && weather.available;
  const hasMessages = messages !== null && messages.length > 0;
  const onVacation = !!vacation?.active;

  return (
    <div className="relative flex h-full w-full flex-col gap-4 px-6 sm:px-8 pt-[38vh] pb-6 text-[color:var(--splash-text)] drop-shadow-[0_2px_8px_rgba(0,0,0,0.45)]">
      <ClockHeader iso={clock.iso_now} timeFormat={timeFormat} weather={weather} showWeather={hasWeather} />

      {onVacation && (
        <div className="flex items-center gap-3 rounded-2xl bg-amber-500/85 px-5 py-3 text-white shadow-lg backdrop-blur">
          <span className="text-2xl" aria-hidden>🏝</span>
          <div className="min-w-0 flex-1">
            <p className="font-semibold leading-tight">
              Household on vacation
              {vacation?.end_date ? ` until ${vacation.end_date}` : ""}
            </p>
            {vacation?.reason && (
              <p className="truncate text-sm opacity-90">{vacation.reason}</p>
            )}
          </div>
        </div>
      )}

      <div className="grid flex-1 min-h-0 grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Agenda spans 2/3 on wide screens — it's the most info-dense
            section and the one most likely to need viewport spill. */}
        {hasAgenda && (
          <SplashCard className="lg:col-span-2 min-h-0 flex flex-col">
            <SectionHeading icon="📅" label="Agenda" />
            <AgendaBlock days={days!} timeFormat={timeFormat} />
          </SplashCard>
        )}

        <div className="flex min-h-0 flex-col gap-4">
          {hasRoutines && (
            <SplashCard className="min-h-0 flex flex-col">
              <SectionHeading icon="✨" label="Today's Routines" />
              <RoutinesBlock routines={routines!} />
            </SplashCard>
          )}

          {hasMeals && (
            <SplashCard className="min-h-0 flex flex-col">
              <SectionHeading icon="🍽️" label="Tonight" />
              <MealsBlock meals={meals!} />
            </SplashCard>
          )}

          {hasMessages && (
            <SplashCard className="min-h-0 flex flex-col">
              <SectionHeading icon="💬" label="Messages" />
              <MessagesBlock messages={messages!} />
            </SplashCard>
          )}
        </div>
      </div>

      <FooterHint />
    </div>
  );
}

/**
 * Translucent card surface used behind every content block. Sits over
 * the Hestia hearth backdrop with a subtle blur + light border so the
 * data reads cleanly against the warm fire.
 */
function SplashCard({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`rounded-2xl p-4 sm:p-5 backdrop-blur-md ring-1 ${className}`}
      style={{
        background: "var(--splash-surface)",
        // ring-1 picks up currentColor by default; force the splash
        // border so the ring isn't tied to text colour.
        boxShadow: "inset 0 0 0 1px var(--splash-border)",
      }}
    >
      {children}
    </section>
  );
}

// ── Header ──────────────────────────────────────────────────────────────────

interface ClockHeaderProps {
  iso: string;
  timeFormat: "12h" | "24h";
  weather: SplashWeather | null;
  showWeather: boolean;
}

function ClockHeader({ iso, timeFormat, weather, showWeather }: ClockHeaderProps) {
  // We re-derive ``now`` locally and tick every minute. The server's
  // ``clock.iso_now`` is treated as a hint (used only for the initial
  // paint before the first interval fires) — once mounted, the wall
  // clock is the source of truth so the displayed minute matches reality.
  const [now, setNow] = useState(() => {
    try {
      return parseISO(iso);
    } catch {
      return new Date();
    }
  });

  useEffect(() => {
    const tick = () => setNow(new Date());
    tick();
    const id = window.setInterval(tick, 60_000);
    return () => window.clearInterval(id);
  }, []);

  return (
    <header className="flex items-end justify-between gap-6">
      <div>
        <div className="text-[clamp(3rem,8vw,6rem)] font-light leading-none tabular-nums tracking-tight">
          {formatTime(now, "h:mm", timeFormat)}
        </div>
        <div className="mt-1 text-[clamp(1rem,2vw,1.5rem)] font-light text-[color:var(--splash-text-muted)]">
          {format(now, "EEEE, MMMM d")}
        </div>
      </div>
      {showWeather && weather && weather.current_temp !== null && <WeatherBlock weather={weather} />}
    </header>
  );
}

function WeatherBlock({ weather }: { weather: SplashWeather }) {
  const unit = weather.units === "metric" ? "°C" : "°F";
  return (
    <div className="text-right">
      <div className="text-[clamp(2.5rem,6vw,5rem)] font-light leading-none tabular-nums">
        {weather.current_temp !== null ? `${Math.round(weather.current_temp)}${unit}` : "—"}
      </div>
      <div className="mt-1 text-base text-[color:var(--splash-text-muted)] capitalize">
        {weather.description ?? ""}
        {weather.high !== null && weather.low !== null && (
          <span className="ml-2 tabular-nums">
            ↑{Math.round(weather.high)}° ↓{Math.round(weather.low)}°
          </span>
        )}
      </div>
    </div>
  );
}

// ── Sections ────────────────────────────────────────────────────────────────

function SectionHeading({ icon, label }: { icon: string; label: string }) {
  return (
    <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.15em] text-[color:var(--splash-text-muted)]">
      <span aria-hidden="true">{icon}</span>
      <span>{label}</span>
    </h2>
  );
}

// Re-export the spill-aware agenda block so tests can exercise it
// directly without rendering the full splash view.
export { AgendaBlock };

function AgendaBlock({ days, timeFormat }: { days: SplashDay[]; timeFormat: "12h" | "24h" }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [visibleCount, setVisibleCount] = useState(days.length);

  // Trim trailing days if the rendered block overflows its parent. We
  // measure after layout, then shrink one day at a time until it fits.
  // The admin's ``splash_agenda_max_days`` gives the upper bound; this
  // viewport pass is the *also-must-fit* guarantee from PRD §2.12.1.
  useLayoutEffect(() => {
    setVisibleCount(days.length);
  }, [days.length]);

  useLayoutEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    let raf = 0;
    const measure = () => {
      const child = el.firstElementChild as HTMLElement | null;
      if (!child) return;
      // ``scrollHeight > clientHeight`` means the day list overflows.
      if (child.scrollHeight > el.clientHeight + 1 && visibleCount > 1) {
        setVisibleCount((c) => Math.max(1, c - 1));
      }
    };
    raf = window.requestAnimationFrame(measure);

    const ro = new ResizeObserver(() => {
      window.cancelAnimationFrame(raf);
      raf = window.requestAnimationFrame(measure);
    });
    ro.observe(el);

    return () => {
      window.cancelAnimationFrame(raf);
      ro.disconnect();
    };
  }, [visibleCount, days]);

  const shown = days.slice(0, visibleCount);
  const hidden = days.length - visibleCount;

  return (
    <div ref={containerRef} className="flex-1 min-h-0 overflow-hidden">
      <div className="space-y-4">
        {shown.map((day) => (
          <DayRow key={day.date} day={day} timeFormat={timeFormat} />
        ))}
        {hidden > 0 && (
          <div className="pt-2 text-sm font-medium text-[color:var(--splash-text-muted)]">
            +{hidden} more {hidden === 1 ? "day" : "days"}
          </div>
        )}
      </div>
    </div>
  );
}

function DayRow({ day, timeFormat }: { day: SplashDay; timeFormat: "12h" | "24h" }) {
  return (
    <div>
      <div className="mb-1.5 text-base font-semibold tracking-tight">{day.label}</div>
      {day.events.length === 0 ? (
        <div className="text-sm italic text-[color:var(--splash-text-muted)]">Nothing scheduled</div>
      ) : (
        <ul className="space-y-1.5">
          {day.events.map((ev) => (
            <EventRow key={ev.id} event={ev} timeFormat={timeFormat} />
          ))}
        </ul>
      )}
    </div>
  );
}

function EventRow({ event, timeFormat }: { event: SplashEvent; timeFormat: "12h" | "24h" }) {
  // The "color dot" denotes WHO the event belongs to (per PRD §2.12.3),
  // so it must remain visible even when ``busy_only`` strips the title.
  const dot = event.profile_color ?? event.color ?? "#9CA3AF";
  let timeLabel: string;
  if (event.all_day) {
    timeLabel = "All day";
  } else {
    try {
      timeLabel = formatTime(parseISO(event.start_time), "h:mm a", timeFormat);
    } catch {
      timeLabel = "—";
    }
  }
  return (
    <li className="flex items-center gap-3">
      <span
        className="h-2.5 w-2.5 shrink-0 rounded-full"
        style={{ backgroundColor: dot }}
        aria-hidden="true"
      />
      <span className="w-20 shrink-0 text-sm tabular-nums text-[color:var(--splash-text-muted)]">
        {timeLabel}
      </span>
      <span className="min-w-0 flex-1 truncate text-base">{event.title}</span>
      {event.location && (
        <span className="hidden truncate text-sm text-[color:var(--splash-text-muted)] md:inline md:max-w-[10rem]">
          {event.location}
        </span>
      )}
    </li>
  );
}

// ── Routines ────────────────────────────────────────────────────────────────

function RoutinesBlock({ routines }: { routines: SplashRoutine[] }) {
  return (
    <ul className="space-y-2 overflow-hidden">
      {routines.slice(0, 6).map((r) => {
        const chip = TIME_BLOCK_COLOR[r.time_block] ?? KID_SAFE_PALETTE.anytime;
        return (
          <li
            key={r.id}
            className="flex items-center gap-3 rounded-xl bg-[color:var(--splash-surface)] px-3 py-2"
          >
            <span
              className="rounded-md px-2 py-0.5 text-xs font-semibold uppercase tracking-wider text-gray-900"
              style={{ backgroundColor: chip }}
            >
              {r.time_block}
            </span>
            <span className="min-w-0 flex-1 truncate text-base font-medium">{r.name}</span>
            {r.assignee && (
              <span
                className="h-6 w-6 shrink-0 rounded-full text-xs font-bold flex items-center justify-center text-white"
                style={{ backgroundColor: r.assignee.color }}
                title={r.assignee.name}
                aria-label={r.assignee.name}
              >
                {r.assignee.name.charAt(0)}
              </span>
            )}
            <span className="shrink-0 text-xs text-[color:var(--splash-text-muted)] tabular-nums">
              {r.step_count} step{r.step_count === 1 ? "" : "s"}
            </span>
            {r.streak_days > 0 && (
              <span
                className="shrink-0 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800"
                title={`${r.streak_days}-day streak`}
              >
                🔥 {r.streak_days}
              </span>
            )}
          </li>
        );
      })}
    </ul>
  );
}

// ── Meals ───────────────────────────────────────────────────────────────────

function MealsBlock({ meals }: { meals: SplashMeal[] }) {
  // Collapse to today + next, and prefer dinner when multiple meals
  // are present for the same day.
  const dinner = meals.find((m) => m.meal_type === "dinner") ?? meals[0];
  return (
    <div className="rounded-xl bg-[color:var(--splash-surface)] p-4">
      <div className="text-xs uppercase tracking-wider text-[color:var(--splash-text-muted)]">
        {dinner.meal_type}
      </div>
      <div className="mt-1 text-lg font-semibold leading-tight">{dinner.title}</div>
    </div>
  );
}

// ── Messages ────────────────────────────────────────────────────────────────

function MessagesBlock({ messages }: { messages: SplashMessage[] }) {
  return (
    <ul className="space-y-2 overflow-hidden">
      {messages.slice(0, 3).map((m) => (
        <li
          key={m.id}
          className="rounded-xl border-l-4 bg-[color:var(--splash-surface)] px-3 py-2"
          style={{ borderLeftColor: m.color || KID_SAFE_PALETTE.morning }}
        >
          <div className="text-sm font-semibold">{m.title}</div>
          {m.body && (
            <div className="mt-0.5 line-clamp-2 text-sm text-[color:var(--splash-text-muted)]">
              {m.body}
            </div>
          )}
        </li>
      ))}
    </ul>
  );
}

// ── Footer ──────────────────────────────────────────────────────────────────

function FooterHint() {
  return (
    <div className="mt-2 text-center text-xs uppercase tracking-[0.3em] text-[color:var(--splash-text-muted)]">
      Tap anywhere to sign in
    </div>
  );
}
