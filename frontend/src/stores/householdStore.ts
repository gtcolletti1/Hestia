import { create } from "zustand";
import {
  profiles as profilesApi,
  households as householdsApi,
} from "@/api/endpoints";
import type { Profile } from "@/types";

interface HouseholdState {
  householdId: string | null;
  householdName: string | null;
  profiles: Profile[];
  initialized: boolean;
  setHouseholdId: (id: string | null) => void;
  setHouseholdName: (name: string | null) => void;
  setProfiles: (profiles: Profile[]) => void;
  fetchProfiles: () => Promise<void>;
  fetchHousehold: () => Promise<void>;
  clear: () => void;
}

export const useHouseholdStore = create<HouseholdState>((set, get) => ({
  householdId: localStorage.getItem("household_id"),
  householdName: localStorage.getItem("household_name"),
  profiles: [],
  initialized: !!localStorage.getItem("household_id"),

  setHouseholdId: (id) => {
    if (id) {
      localStorage.setItem("household_id", id);
    } else {
      localStorage.removeItem("household_id");
    }
    set({ householdId: id, initialized: !!id });
  },

  setHouseholdName: (name) => {
    if (name) {
      localStorage.setItem("household_name", name);
    } else {
      localStorage.removeItem("household_name");
    }
    set({ householdName: name });
  },

  setProfiles: (profiles) => set({ profiles }),

  fetchProfiles: async () => {
    const householdId = get().householdId;
    if (!householdId) return;
    const { data } = await profilesApi.getAll(householdId);
    set({ profiles: data });
  },

  fetchHousehold: async () => {
    const householdId = get().householdId;
    if (!householdId) return;
    const { data } = await householdsApi.getOne(householdId);
    set({ householdName: data.name, profiles: data.profiles });
    localStorage.setItem("household_name", data.name);
  },

  clear: () => {
    localStorage.removeItem("household_id");
    localStorage.removeItem("household_name");
    set({
      householdId: null,
      householdName: null,
      profiles: [],
      initialized: false,
    });
  },
}));
