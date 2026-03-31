const THEME_KEY = "family-hub-theme";

export type Theme = "light" | "dark";

export function getTheme(): Theme {
  const stored = localStorage.getItem(THEME_KEY);
  if (stored === "light" || stored === "dark") return stored;
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

export function setTheme(theme: Theme): void {
  localStorage.setItem(THEME_KEY, theme);
  applyTheme(theme);
}

export function toggleTheme(): Theme {
  const next = getTheme() === "dark" ? "light" : "dark";
  setTheme(next);
  return next;
}

export function applyTheme(theme?: Theme): void {
  const resolved = theme ?? getTheme();
  document.documentElement.classList.toggle("dark", resolved === "dark");
}
