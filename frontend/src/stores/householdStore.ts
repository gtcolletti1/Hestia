import { create } from "zustand";
import {
  profiles as profilesApi,
  households as householdsApi,
  setup as setupApi,
  type HouseholdSummary,
} from "@/api/endpoints";
import type { Profile } from "@/types";

export type BootStatus =
  | "checking"
  | "needs-setup"
  | "needs-pick"
  | "ready"
  | "error";

interface HouseholdState {
  householdId: string | null;
  householdName: string | null;
  profiles: Profile[];
  initialized: boolean;
  bootStatus: BootStatus;
  discoveredHouseholds: HouseholdSummary[];
  setHouseholdId: (id: string | null) => void;
  setHouseholdName: (name: string | null) => void;
  setProfiles: (profiles: Profile[]) => void;
  fetchProfiles: () => Promise<void>;
  fetchHousehold: () => Promise<void>;
  /**
   * Ask the backend which households exist and decide the boot path.
   *
   * - 0 households                          → bootStatus = "needs-setup"
   * - 1 household, no stored selection       → auto-select it; bootStatus = "ready"
   * - 1 household, stored selection matches  → keep it; bootStatus = "ready"
   * - 1 household, stored selection stale    → replace with the real one; bootStatus = "ready"
   * - >1 households, stored selection valid  → keep it; bootStatus = "ready"
   * - >1 households, no/stale selection      → bootStatus = "needs-pick"
   *
   * Errors are reported via the returned promise but do not throw — callers
   * can decide how to retry.
   */
  discover: () => Promise<void>;
  selectHousehold: (id: string, name: string) => void;
  clear: () => void;
}

const writeStored = (id: string | null, name: string | null) => {
  if (id) localStorage.setItem("household_id", id);
  else localStorage.removeItem("household_id");
  if (name) localStorage.setItem("household_name", name);
  else localStorage.removeItem("household_name");
};

export const useHouseholdStore = create<HouseholdState>((set, get) => ({
  householdId: localStorage.getItem("household_id"),
  householdName: localStorage.getItem("household_name"),
  profiles: [],
  initialized: !!localStorage.getItem("household_id"),
  bootStatus: "checking",
  discoveredHouseholds: [],

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

  discover: async () => {
    set({ bootStatus: "checking" });
    let data;
    try {
      const resp = await setupApi.discover();
      data = resp.data;
    } catch {
      // Don't clobber an already-valid stored selection — keep the user
      // in their last known state if the network blip is transient.
      // Surface as a retryable error so the UI can decide what to do.
      set({ bootStatus: "error" });
      return;
    }
    const stored = get().householdId;
    const list = data.households;

    if (data.setup_required || list.length === 0) {
      // Server says no households exist; clear any stale local pointer
      // and any in-memory profile cache from a deleted household.
      writeStored(null, null);
      set({
        householdId: null,
        householdName: null,
        profiles: [],
        initialized: false,
        discoveredHouseholds: [],
        bootStatus: "needs-setup",
      });
      return;
    }

    const storedMatch = stored ? list.find((h) => h.id === stored) : undefined;

    if (storedMatch) {
      // Refresh the cached name in case it changed server-side.
      writeStored(storedMatch.id, storedMatch.name);
      set({
        householdId: storedMatch.id,
        householdName: storedMatch.name,
        initialized: true,
        discoveredHouseholds: list,
        bootStatus: "ready",
      });
      return;
    }

    if (list.length === 1) {
      const only = list[0];
      writeStored(only.id, only.name);
      set({
        householdId: only.id,
        householdName: only.name,
        // Clear any stale profile cache from a previous (now-replaced) household.
        profiles: [],
        initialized: true,
        discoveredHouseholds: list,
        bootStatus: "ready",
      });
      return;
    }

    // Multiple households exist and we have no valid stored selection —
    // user has to pick. Clear any stale stored id so we don't render
    // ProfileSelector against the wrong household, and drop any
    // previously-cached profiles.
    writeStored(null, null);
    set({
      householdId: null,
      householdName: null,
      profiles: [],
      initialized: false,
      discoveredHouseholds: list,
      bootStatus: "needs-pick",
    });
  },

  selectHousehold: (id, name) => {
    writeStored(id, name);
    set({
      householdId: id,
      householdName: name,
      // Drop any cached profiles from a different household.
      profiles: [],
      initialized: true,
      bootStatus: "ready",
    });
  },

  clear: () => {
    localStorage.removeItem("household_id");
    localStorage.removeItem("household_name");
    set({
      householdId: null,
      householdName: null,
      profiles: [],
      initialized: false,
      bootStatus: "checking",
      discoveredHouseholds: [],
    });
  },
}));
