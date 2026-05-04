export interface Profile {
  id: string;
  name: string;
  color: string;
  avatar_url?: string;
  role: "admin" | "standard" | "kid";
  household_id: string;
  is_active: boolean;
}

export interface Event {
  id: string;
  title: string;
  description?: string;
  location?: string;
  start_time: string;
  end_time: string;
  all_day: boolean;
  recurrence_rule?: string;
  color?: string;
  is_private: boolean;
  source_calendar_id: string;
  profile_id?: string;
}

export interface Routine {
  id: string;
  name: string;
  time_block: "morning" | "afternoon" | "evening" | "bedtime";
  days_of_week: number[];
  start_time?: string;
  is_active: boolean;
  pausable_on_vacation?: boolean;
  household_id: string;
  profile_id?: string;
  steps: RoutineStep[];
}

export interface RoutineStep {
  id: string;
  label: string;
  icon?: string;
  sort_order: number;
  points_value: number;
  days_of_week?: number[] | null;
}

export interface RoutineCompletion {
  id: string;
  routine_id: string;
  profile_id: string;
  date: string;
  completed_steps: string[];
  is_fully_completed: boolean;
}

export interface TodayCompletion {
  routine_id: string;
  profile_id: string;
  completed_step_ids: string[];
  applicable_step_ids: string[];
  is_fully_completed: boolean;
}

export interface RoutineTemplateStep {
  label: string;
  icon?: string;
  points_value: number;
}

export interface RoutineTemplate {
  id: string;
  name: string;
  description: string;
  icon: string;
  time_block: Routine["time_block"];
  days_of_week: number[];
  steps: RoutineTemplateStep[];
}

export interface TaskList {
  id: string;
  name: string;
  category: string;
  icon?: string;
  household_id: string;
  is_archived: boolean;
  items: ListItem[];
  item_count: number;
  checked_count: number;
}

export interface ListItem {
  id: string;
  list_id: string;
  text: string;
  is_checked: boolean;
  sort_order: number;
  assigned_profile_id?: string;
  due_date?: string;
}

export interface MealPlan {
  id: string;
  date: string;
  meal_type: "breakfast" | "lunch" | "dinner" | "snack";
  title: string;
  description?: string;
  recipe_url?: string;
  household_id: string;
  assigned_profile_id?: string;
}

export interface DashboardRoutine {
  id: string;
  name: string;
  time_block: "morning" | "afternoon" | "evening" | "bedtime";
  profile_id?: string | null;
  step_count: number;
  streak_days?: number;
}

export interface VacationStatus {
  active: boolean;
  reason?: string | null;
  end_date?: string | null;
}

export interface DashboardData {
  date: string;
  profiles: Profile[];
  agenda: AgendaBucket[];
  active_routines: DashboardRoutine[];
  today_meals: MealPlan[];
  active_lists: {
    name: string;
    item_count: number;
    checked_count: number;
  }[];
  vacation?: VacationStatus | null;
}

export interface AgendaBucket {
  bucket: string;
  events: EventSummary[];
}

export interface EventSummary {
  id: string;
  title: string;
  start_time: string;
  end_time: string;
  color?: string;
  profile_name?: string;
  location?: string;
}
