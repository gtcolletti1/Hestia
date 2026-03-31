import { create } from "zustand";
import client from "@/api/client";
import type { Profile } from "@/types";

interface HouseholdState {
  householdId: string | null;
  profiles: Profile[];
  setHouseholdId: (id: string | null) => void;
  setProfiles: (profiles: Profile[]) => void;
  fetchProfiles: () => Promise<void>;
}

export const useHouseholdStore = create<HouseholdState>((set, get) => ({
  householdId: null,
  profiles: [],

  setHouseholdId: (id) => set({ householdId: id }),

  setProfiles: (profiles) => set({ profiles }),

  fetchProfiles: async () => {
    const householdId = get().householdId;
    if (!householdId) return;
    const { data } = await client.get<Profile[]>(
      `/households/${householdId}/profiles`,
    );
    set({ profiles: data });
  },
}));
