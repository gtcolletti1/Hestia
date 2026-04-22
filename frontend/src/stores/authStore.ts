import { create } from "zustand";

interface Profile {
  id: string;
  name: string;
  avatar?: string;
  role: "admin" | "standard" | "kid";
}

interface AuthState {
  token: string | null;
  profile: Profile | null;
  isAuthenticated: boolean;
  login: (token: string, profile: Profile) => void;
  logout: () => void;
  setProfile: (profile: Profile) => void;
}

const PROFILE_KEY = "auth_profile";

function loadProfile(): Profile | null {
  try {
    const raw = localStorage.getItem(PROFILE_KEY);
    return raw ? (JSON.parse(raw) as Profile) : null;
  } catch {
    return null;
  }
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem("auth_token"),
  profile: loadProfile(),
  isAuthenticated: !!localStorage.getItem("auth_token"),

  login: (token, profile) => {
    localStorage.setItem("auth_token", token);
    localStorage.setItem(PROFILE_KEY, JSON.stringify(profile));
    set({ token, profile, isAuthenticated: true });
  },

  logout: () => {
    localStorage.removeItem("auth_token");
    localStorage.removeItem(PROFILE_KEY);
    set({ token: null, profile: null, isAuthenticated: false });
  },

  setProfile: (profile) => {
    localStorage.setItem(PROFILE_KEY, JSON.stringify(profile));
    set({ profile });
  },
}));
