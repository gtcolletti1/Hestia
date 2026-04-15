import type { Event, Profile } from "@/types";

export interface CalendarEvent {
  id: string;
  title: string;
  start: string;
  end: string;
  location?: string;
  description?: string;
  profile_id: string;
  profile_name: string;
  profile_color: string;
  calendar_source?: string;
  all_day?: boolean;
  recurrence_rule?: string;
}

export interface EventFormData {
  title: string;
  start: string;
  end: string;
  location: string;
  description: string;
  profile_id: string;
  all_day: boolean;
  recurrence_rule: string;
}

export type CalendarViewMode = "day" | "week" | "month" | "agenda";

export const RECURRENCE_OPTIONS = [
  { value: "", label: "Does not repeat" },
  { value: "FREQ=DAILY", label: "Daily" },
  { value: "FREQ=WEEKLY", label: "Weekly" },
  { value: "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR", label: "Weekdays" },
  { value: "FREQ=MONTHLY", label: "Monthly" },
  { value: "FREQ=YEARLY", label: "Yearly" },
] as const;

export function recurrenceLabel(rule?: string): string {
  if (!rule) return "";
  const match = RECURRENCE_OPTIONS.find((o) => o.value === rule);
  if (match) return match.label;
  if (rule.includes("DAILY")) return "Daily";
  if (rule.includes("WEEKLY")) return "Weekly";
  if (rule.includes("MONTHLY")) return "Monthly";
  if (rule.includes("YEARLY")) return "Yearly";
  return "Repeats";
}

export function mapEventToCalendarEvent(
  ev: Event,
  profiles: Profile[],
): CalendarEvent {
  const profile = profiles.find((p) => p.id === ev.profile_id);
  return {
    id: ev.id,
    title: ev.title,
    start: ev.start_time,
    end: ev.end_time,
    location: ev.location,
    description: ev.description,
    profile_id: ev.profile_id ?? "",
    profile_name: profile?.name ?? "",
    profile_color: profile?.color ?? ev.color ?? "",
    calendar_source: ev.source_calendar_id,
    all_day: ev.all_day,
    recurrence_rule: ev.recurrence_rule,
  };
}
