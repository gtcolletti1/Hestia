import { create } from "zustand";
import { persist } from "zustand/middleware";

type Theme = "light" | "dark";

interface ThemeState {
  theme: Theme;
  accentColor: string;
  highContrast: boolean;
  setTheme: (theme: Theme) => void;
  setAccentColor: (color: string) => void;
  toggleHighContrast: () => void;
}

/** Apply the current theme to the document root so Tailwind/CSS can react. */
function applyTheme(theme: Theme, accentColor: string, highContrast: boolean) {
  const root = document.documentElement;

  // Toggle dark mode class
  if (theme === "dark") {
    root.classList.add("dark");
  } else {
    root.classList.remove("dark");
  }

  // High contrast class
  if (highContrast) {
    root.classList.add("high-contrast");
  } else {
    root.classList.remove("high-contrast");
  }

  // Expose accent color as a CSS custom property
  root.style.setProperty("--accent-color", accentColor);
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      theme: "light",
      accentColor: "#3b82f6",
      highContrast: false,

      setTheme: (theme) =>
        set((state) => {
          applyTheme(theme, state.accentColor, state.highContrast);
          return { theme };
        }),

      setAccentColor: (accentColor) =>
        set((state) => {
          applyTheme(state.theme, accentColor, state.highContrast);
          return { accentColor };
        }),

      toggleHighContrast: () =>
        set((state) => {
          const next = !state.highContrast;
          applyTheme(state.theme, state.accentColor, next);
          return { highContrast: next };
        }),
    }),
    {
      name: "family-hub-theme",
      onRehydrateStorage: () => (state) => {
        if (state) {
          applyTheme(state.theme, state.accentColor, state.highContrast);
        }
      },
    },
  ),
);
