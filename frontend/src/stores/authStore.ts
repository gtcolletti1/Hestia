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

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem("auth_token"),
  profile: null,
  isAuthenticated: !!localStorage.getItem("auth_token"),

  login: (token, profile) => {
    localStorage.setItem("auth_token", token);
    set({ token, profile, isAuthenticated: true });
  },

  logout: () => {
    localStorage.removeItem("auth_token");
    set({ token: null, profile: null, isAuthenticated: false });
  },

  setProfile: (profile) => {
    set({ profile });
  },
}));
