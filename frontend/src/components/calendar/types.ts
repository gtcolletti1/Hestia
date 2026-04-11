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
}

export interface EventFormData {
  title: string;
  start: string;
  end: string;
  location: string;
  description: string;
  profile_id: string;
  all_day: boolean;
}

export type CalendarViewMode = "day" | "week" | "month" | "agenda";

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
  };
}
