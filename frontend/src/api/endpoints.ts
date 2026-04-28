import client from "./client";
import type {
  Profile,
  Event,
  Routine,
  RoutineStep,
  RoutineCompletion,
  TaskList,
  ListItem,
  MealPlan,
  DashboardData,
} from "@/types";

// --- Profiles ---

export const profiles = {
  getAll: (householdId: string) =>
    client.get<Profile[]>("/profiles", {
      params: { household_id: householdId },
    }),

  getOne: (id: string) => client.get<Profile>(`/profiles/${id}`),

  create: (data: {
    name: string;
    color: string;
    role: string;
    household_id: string;
    pin?: string;
  }) => client.post<Profile>("/profiles", data),

  update: (id: string, data: Partial<Profile>) =>
    client.put<Profile>(`/profiles/${id}`, data),

  delete: (id: string) => client.delete(`/profiles/${id}`),
};

// --- Households ---

export const households = {
  create: (data: { name: string }) =>
    client.post<{ id: string; name: string }>("/households", data),

  getOne: (householdId: string) =>
    client.get<{ id: string; name: string; profiles: Profile[] }>(
      `/households/${householdId}`,
    ),
};

// --- Setup / discovery (unauthenticated, pre-login) ---

export interface HouseholdSummary {
  id: string;
  name: string;
}

export interface SetupDiscoverResponse {
  setup_required: boolean;
  households: HouseholdSummary[];
}

export const setup = {
  discover: () => client.get<SetupDiscoverResponse>("/setup/discover"),
};

// --- Events ---

export const events = {
  getAll: (
    householdId: string,
    params: {
      start_date: string;
      end_date: string;
      profile_id?: string;
      source_calendar_id?: string;
    },
  ) =>
    client.get<Event[]>("/events", {
      params: { household_id: householdId, ...params },
    }),

  getOne: (eventId: string) => client.get<Event>(`/events/${eventId}`),

  create: (data: Partial<Event> & { source_calendar_id: string }) =>
    client.post<Event>("/events", data),

  update: (eventId: string, data: Partial<Event>) =>
    client.put<Event>(`/events/${eventId}`, data),

  delete: (eventId: string) => client.delete(`/events/${eventId}`),
};

// --- Calendars (source calendars) ---

export const calendars = {
  getAll: (householdId: string) =>
    client.get("/calendars", {
      params: { household_id: householdId },
    }),

  create: (data: { name: string; household_id: string }) =>
    client.post("/calendars", data),

  update: (calendarId: string, data: Record<string, unknown>) =>
    client.put(`/calendars/${calendarId}`, data),

  delete: (calendarId: string) => client.delete(`/calendars/${calendarId}`),
};

// --- Routines ---

export const routines = {
  getAll: (
    householdId: string,
    params?: { profile_id?: string; time_block?: string },
  ) =>
    client.get<Routine[]>("/routines", {
      params: { household_id: householdId, ...params },
    }),

  getOne: (routineId: string) =>
    client.get<Routine>(`/routines/${routineId}`),

  create: (
    data: Partial<Routine> & {
      household_id: string;
      steps: Partial<RoutineStep>[];
    },
  ) => client.post<Routine>("/routines", data),

  update: (routineId: string, data: Partial<Routine>) =>
    client.put<Routine>(`/routines/${routineId}`, data),

  delete: (routineId: string) => client.delete(`/routines/${routineId}`),

  duplicate: (routineId: string) =>
    client.post<Routine>(`/routines/${routineId}/duplicate`),

  completeStep: (
    routineId: string,
    stepId: string,
    profileId: string,
  ) =>
    client.post<RoutineCompletion>(
      `/routines/${routineId}/steps/${stepId}/complete`,
      null,
      { params: { profile_id: profileId } },
    ),

  getStreak: (routineId: string, profileId: string) =>
    client.get<{ streak: number }>(`/routines/${routineId}/streak`, {
      params: { profile_id: profileId },
    }),

  getActive: (
    householdId: string,
    params?: { profile_id?: string },
  ) =>
    client.get<Routine[]>("/routines/active", {
      params: { household_id: householdId, ...params },
    }),
};

// --- Lists ---

export const lists = {
  getAll: (householdId: string, params?: { category?: string }) =>
    client.get<TaskList[]>("/lists", {
      params: { household_id: householdId, ...params },
    }),

  getOne: (listId: string) =>
    client.get<TaskList>(`/lists/${listId}`),

  create: (data: Partial<TaskList> & { household_id: string }) =>
    client.post<TaskList>("/lists", data),

  update: (listId: string, data: Partial<TaskList>) =>
    client.put<TaskList>(`/lists/${listId}`, data),

  delete: (listId: string) => client.delete(`/lists/${listId}`),

  addItem: (listId: string, data: Partial<ListItem>) =>
    client.post<ListItem>(`/lists/${listId}/items`, data),

  updateItem: (listId: string, itemId: string, data: Partial<ListItem>) =>
    client.put<ListItem>(`/lists/${listId}/items/${itemId}`, data),

  deleteItem: (listId: string, itemId: string) =>
    client.delete(`/lists/${listId}/items/${itemId}`),

  toggleItem: (listId: string, itemId: string) =>
    client.patch<ListItem>(`/lists/${listId}/items/${itemId}/toggle`),

  reorder: (listId: string, data: { item_ids: string[] }) =>
    client.put(`/lists/${listId}/reorder`, data),
};

// --- Meals ---

export const meals = {
  getAll: (
    householdId: string,
    params?: {
      date?: string;
      start_date?: string;
      end_date?: string;
    },
  ) =>
    client.get<MealPlan[]>("/meals", {
      params: { household_id: householdId, ...params },
    }),

  getOne: (mealId: string) => client.get<MealPlan>(`/meals/${mealId}`),

  create: (data: Partial<MealPlan> & { household_id: string }) =>
    client.post<MealPlan>("/meals", data),

  update: (mealId: string, data: Partial<MealPlan>) =>
    client.put<MealPlan>(`/meals/${mealId}`, data),

  delete: (mealId: string) => client.delete(`/meals/${mealId}`),

  getWeekly: (householdId: string, weekStart: string) =>
    client.get<{ week_start: string; days: Array<{ date: string; meals: MealPlan[] }> }>("/meals/week", {
      params: { household_id: householdId, week_start: weekStart },
    }),
};

// --- Dashboard ---

// Resolve the browser's IANA timezone once at module load. The dashboard
// uses this to compute "today's agenda" against the user's wall clock,
// not the backend container's UTC clock.
const browserTz =
  typeof Intl !== "undefined"
    ? Intl.DateTimeFormat().resolvedOptions().timeZone
    : undefined;

export const dashboard = {
  get: (householdId: string) =>
    client.get<DashboardData>("/dashboard", {
      params: { household_id: householdId, ...(browserTz ? { tz: browserTz } : {}) },
    }),
};

// --- Admin ---

export const admin = {
  getSettings: (householdId: string) =>
    client.get("/admin/settings", {
      params: { household_id: householdId },
    }),

  updateSettings: (householdId: string, data: Record<string, unknown>) =>
    client.put("/admin/settings", data, {
      params: { household_id: householdId },
    }),

  toggleModule: (householdId: string, data: { module: string; enabled: boolean }) =>
    client.patch("/admin/modules", data, {
      params: { household_id: householdId },
    }),
};

// --- Auth ---

export const auth = {
  login: (data: { profile_id: string; pin: string }) =>
    client.post<{ access_token: string; token_type: string; profile: { id: string; name: string; role: "admin" | "standard" | "kid"; color: string; avatar_url?: string; household_id: string } }>("/auth/login", data),

  me: () => client.get<Profile>("/auth/me"),
};

// --- Integrations ---

export const integrations = {
  getGoogleAuthUrl: (householdId: string) =>
    client.get<{ url: string }>("/integrations/oauth/google/authorize", {
      params: { household_id: householdId },
    }),

  getMicrosoftAuthUrl: (householdId: string) =>
    client.get<{ url: string }>("/integrations/oauth/microsoft/authorize", {
      params: { household_id: householdId },
    }),

  getStatus: (householdId: string) =>
    client.get("/integrations/status", {
      params: { household_id: householdId },
    }),

  subscribeIcal: (data: {
    household_id: string;
    name: string;
    ical_url: string;
    color?: string;
  }) =>
    client.post<{
      id: string;
      name: string;
      provider: string;
      events_preview_count: number;
      sync_queued: boolean;
    }>("/integrations/ical/subscribe", data),

  unsubscribeIcal: (calendarId: string) =>
    client.delete(`/integrations/ical/${calendarId}`),

  syncCalendar: (calendarId: string) =>
    client.get(`/integrations/calendars/sync/${calendarId}`),
};

// --- Weather ---

export const weather = {
  get: (householdId: string) =>
    client.get("/weather", {
      params: { household_id: householdId },
    }),
};

// --- Photos ---

export const photos = {
  getAll: (householdId: string) =>
    client.get("/photos", {
      params: { household_id: householdId },
    }),

  create: (data: { url: string; caption?: string; sort_order?: number; household_id: string }) =>
    client.post("/photos", data),

  upload: (formData: FormData) =>
    client.post("/photos/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),

  update: (photoId: string, data: { caption?: string; sort_order?: number }) =>
    client.put(`/photos/${photoId}`, data),

  delete: (photoId: string) => client.delete(`/photos/${photoId}`),
};

// --- Notes (Message Board) ---

export const notes = {
  getAll: (householdId: string) =>
    client.get("/notes", {
      params: { household_id: householdId },
    }),

  create: (data: { title: string; body?: string; color?: string; pinned?: boolean; household_id: string }) =>
    client.post("/notes", data),

  update: (noteId: string, data: { title?: string; body?: string; color?: string; pinned?: boolean; sort_order?: number }) =>
    client.put(`/notes/${noteId}`, data),

  delete: (noteId: string) => client.delete(`/notes/${noteId}`),
};

// --- Reminders & Notifications ---

export const reminders = {
  create: (data: { event_id: string; minutes_before: number; household_id: string }) =>
    client.post("/reminders", data),

  getForEvent: (eventId: string, householdId: string) =>
    client.get("/reminders", {
      params: { event_id: eventId, household_id: householdId },
    }),

  delete: (reminderId: string) => client.delete(`/reminders/${reminderId}`),
};

export const notifications = {
  getUpcoming: (householdId: string) =>
    client.get("/notifications/upcoming", {
      params: { household_id: householdId },
    }),
};

// --- Rewards ---

export const rewards = {
  getAll: (householdId: string) =>
    client.get("/rewards", {
      params: { household_id: householdId },
    }),

  create: (data: { title: string; description?: string; points_cost: number; icon?: string; household_id: string }) =>
    client.post("/rewards", data),

  update: (rewardId: string, data: { title?: string; description?: string; points_cost?: number; icon?: string; is_active?: boolean }) =>
    client.put(`/rewards/${rewardId}`, data),

  delete: (rewardId: string) => client.delete(`/rewards/${rewardId}`),

  getPoints: (profileId: string, householdId: string) =>
    client.get("/rewards/points", {
      params: { profile_id: profileId, household_id: householdId },
    }),

  getLeaderboard: (householdId: string) =>
    client.get("/rewards/leaderboard", {
      params: { household_id: householdId },
    }),

  redeem: (data: { reward_id: string; profile_id: string; household_id: string }) =>
    client.post("/rewards/redeem", data),
};
