import client from "./client";
import type {
  Profile,
  Event,
  Routine,
  RoutineCompletion,
  TaskList,
  ListItem,
  MealPlan,
  DashboardData,
} from "@/types";

// --- Profiles ---

export const profiles = {
  getAll: (householdId: string) =>
    client.get<Profile[]>(`/households/${householdId}/profiles`),

  create: (householdId: string, data: Partial<Profile>) =>
    client.post<Profile>(`/households/${householdId}/profiles`, data),

  update: (householdId: string, profileId: string, data: Partial<Profile>) =>
    client.patch<Profile>(
      `/households/${householdId}/profiles/${profileId}`,
      data,
    ),

  delete: (householdId: string, profileId: string) =>
    client.delete(`/households/${householdId}/profiles/${profileId}`),
};

// --- Calendar ---

export const calendar = {
  getEvents: (householdId: string, params?: { start?: string; end?: string }) =>
    client.get<Event[]>(`/households/${householdId}/events`, { params }),

  createEvent: (householdId: string, data: Partial<Event>) =>
    client.post<Event>(`/households/${householdId}/events`, data),

  updateEvent: (householdId: string, eventId: string, data: Partial<Event>) =>
    client.patch<Event>(`/households/${householdId}/events/${eventId}`, data),

  deleteEvent: (householdId: string, eventId: string) =>
    client.delete(`/households/${householdId}/events/${eventId}`),
};

// --- Routines ---

export const routines = {
  getAll: (householdId: string) =>
    client.get<Routine[]>(`/households/${householdId}/routines`),

  getActive: (householdId: string, params?: { profile_id?: string }) =>
    client.get<Routine[]>(`/households/${householdId}/routines/active`, {
      params,
    }),

  completeStep: (
    householdId: string,
    routineId: string,
    data: { profile_id: string; step_id: string; date: string },
  ) =>
    client.post<RoutineCompletion>(
      `/households/${householdId}/routines/${routineId}/complete-step`,
      data,
    ),

  getStreak: (
    householdId: string,
    routineId: string,
    profileId: string,
  ) =>
    client.get<{ streak: number }>(
      `/households/${householdId}/routines/${routineId}/streak/${profileId}`,
    ),
};

// --- Lists ---

export const lists = {
  getAll: (householdId: string) =>
    client.get<TaskList[]>(`/households/${householdId}/lists`),

  create: (householdId: string, data: Partial<TaskList>) =>
    client.post<TaskList>(`/households/${householdId}/lists`, data),

  addItem: (householdId: string, listId: string, data: Partial<ListItem>) =>
    client.post<ListItem>(
      `/households/${householdId}/lists/${listId}/items`,
      data,
    ),

  toggleItem: (householdId: string, listId: string, itemId: string) =>
    client.patch<ListItem>(
      `/households/${householdId}/lists/${listId}/items/${itemId}/toggle`,
    ),

  deleteItem: (householdId: string, listId: string, itemId: string) =>
    client.delete(
      `/households/${householdId}/lists/${listId}/items/${itemId}`,
    ),
};

// --- Meals ---

export const meals = {
  getByDate: (householdId: string, date: string) =>
    client.get<MealPlan[]>(`/households/${householdId}/meals`, {
      params: { date },
    }),

  getWeekly: (householdId: string, startDate: string) =>
    client.get<MealPlan[]>(`/households/${householdId}/meals/week`, {
      params: { start_date: startDate },
    }),

  create: (householdId: string, data: Partial<MealPlan>) =>
    client.post<MealPlan>(`/households/${householdId}/meals`, data),

  update: (householdId: string, mealId: string, data: Partial<MealPlan>) =>
    client.patch<MealPlan>(
      `/households/${householdId}/meals/${mealId}`,
      data,
    ),

  delete: (householdId: string, mealId: string) =>
    client.delete(`/households/${householdId}/meals/${mealId}`),
};

// --- Dashboard ---

export const dashboard = {
  get: (householdId: string) =>
    client.get<DashboardData>(`/households/${householdId}/dashboard`),
};
