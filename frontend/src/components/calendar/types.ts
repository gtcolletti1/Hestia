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
