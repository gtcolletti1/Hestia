/**
 * Types for the public ``GET /api/splash`` response.
 *
 * The backend enforces the household's privacy policy server-side and
 * elides fields the policy hides:
 *  - ``days``, ``routines``, ``meals``, ``messages``, ``weather`` are
 *    each ``null`` when the corresponding splash_show_* toggle is off
 *    (or, for ``days``, when ``splash_calendar_mode === "hidden"``).
 *  - When ``splash_calendar_mode === "busy_only"``, every event is
 *    returned with ``title === "Busy"`` and ``location === null`` —
 *    the original strings are never sent to the client.
 */

export type SplashMode = "ambient" | "photo" | "alternating";
export type SplashCalendarMode = "off" | "busy_only" | "hidden";

export interface SplashClock {
  date: string;
  iso_now: string;
  timezone: string;
  time_format: "12h" | "24h";
}

export interface SplashEvent {
  id: string;
  title: string;
  location: string | null;
  start_time: string;
  end_time: string;
  all_day: boolean;
  color: string | null;
  profile_name: string | null;
  profile_color: string | null;
}

export interface SplashDay {
  date: string;
  label: string;
  events: SplashEvent[];
}

export interface SplashRoutineAssignee {
  id: string;
  name: string;
  color: string;
  avatar_url: string | null;
}

export interface SplashRoutine {
  id: string;
  name: string;
  time_block: "morning" | "afternoon" | "evening" | "anytime";
  step_count: number;
  streak_days: number;
  assignee: SplashRoutineAssignee | null;
}

export interface SplashMeal {
  id: string;
  date: string;
  meal_type: "breakfast" | "lunch" | "dinner" | "snack";
  title: string;
}

export interface SplashMessage {
  id: string;
  title: string;
  body: string;
  color: string;
  pinned: boolean;
  author_name: string | null;
}

export interface SplashWeather {
  available: boolean;
  units: "imperial" | "metric" | null;
  current_temp: number | null;
  high: number | null;
  low: number | null;
  description: string | null;
  icon: string | null;
}

export interface SplashPolicy {
  splash_mode: SplashMode;
  splash_alternating_ambient_seconds: number;
  splash_alternating_photo_seconds: number;
  splash_calendar_mode: SplashCalendarMode;
  splash_agenda_max_days: number;
  show_routines: boolean;
  show_meals: boolean;
  show_weather: boolean;
  show_messages: boolean;
}

export interface SplashVacation {
  active: boolean;
  reason?: string | null;
  end_date?: string | null;
}

export interface SplashSchoolDay {
  is_school_day: boolean;
  reason?: string | null;
  hidden_step_count?: number;
}

export interface SplashResponse {
  household_id: string;
  household_name: string;
  clock: SplashClock;
  days: SplashDay[] | null;
  routines: SplashRoutine[] | null;
  meals: SplashMeal[] | null;
  messages: SplashMessage[] | null;
  weather: SplashWeather | null;
  policy: SplashPolicy;
  vacation?: SplashVacation | null;
  school_day?: SplashSchoolDay | null;
}
