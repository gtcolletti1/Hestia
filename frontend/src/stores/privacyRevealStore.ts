import { create } from "zustand";

const REVEAL_DURATION_MS = 5 * 60 * 1000;
const STORAGE_KEY = "privacy-reveal-expires-at";

interface PrivacyRevealState {
  /** Wall-clock timestamp (ms) when the current reveal window expires.
   *  null means privacy is currently locked. */
  expiresAt: number | null;
  /** True if the reveal is currently active (not yet expired). */
  isRevealed: () => boolean;
  /** Mark the wall display as unlocked for `REVEAL_DURATION_MS`. */
  reveal: () => void;
  /** Re-lock immediately. */
  lock: () => void;
  /** Internal — checks expiry and clears state if past. */
  _tick: () => void;
}

function loadInitialExpiry(): number | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const ts = Number(raw);
    if (!Number.isFinite(ts) || ts <= Date.now()) {
      sessionStorage.removeItem(STORAGE_KEY);
      return null;
    }
    return ts;
  } catch {
    return null;
  }
}

export const usePrivacyRevealStore = create<PrivacyRevealState>((set, get) => ({
  expiresAt: loadInitialExpiry(),

  isRevealed: () => {
    const ts = get().expiresAt;
    return ts !== null && ts > Date.now();
  },

  reveal: () => {
    const ts = Date.now() + REVEAL_DURATION_MS;
    try {
      sessionStorage.setItem(STORAGE_KEY, String(ts));
    } catch {
      // sessionStorage may be unavailable (private mode); reveal still
      // works for the current page lifetime via in-memory state.
    }
    set({ expiresAt: ts });
  },

  lock: () => {
    try {
      sessionStorage.removeItem(STORAGE_KEY);
    } catch {
      /* ignore */
    }
    set({ expiresAt: null });
  },

  _tick: () => {
    const ts = get().expiresAt;
    if (ts !== null && ts <= Date.now()) {
      try {
        sessionStorage.removeItem(STORAGE_KEY);
      } catch {
        /* ignore */
      }
      set({ expiresAt: null });
    }
  },
}));

export const PRIVACY_REVEAL_DURATION_MS = REVEAL_DURATION_MS;
