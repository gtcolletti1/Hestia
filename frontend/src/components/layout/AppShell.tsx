import { useEffect, useMemo, useState, useRef } from "react";
import { NavLink, Outlet, useLocation, Link } from "react-router-dom";
import Clock from "@/components/shared/Clock";
import HestiaLogo from "@/components/shared/HestiaLogo";
import NotificationToast from "@/components/shared/NotificationToast";
import { useHouseholdStore } from "@/stores/householdStore";
import { useAuthStore } from "@/stores/authStore";
import { useNotifications } from "@/hooks/useNotifications";
import { useHouseholdSettings } from "@/hooks/useHouseholdSettings";

const navItems = [
  { to: "/", icon: "🏠", label: "Home", module: null },
  { to: "/calendar", icon: "📅", label: "Calendar", module: "calendar" as const },
  { to: "/routines", icon: "✅", label: "Routines", module: "routines" as const },
  { to: "/lists", icon: "📋", label: "Lists", module: "lists" as const },
  { to: "/meals", icon: "🍽️", label: "Meals", module: "meals" as const },
  { to: "/messages", icon: "💬", label: "Messages", module: "messages" as const },
  { to: "/rewards", icon: "🏆", label: "Rewards", module: "rewards" as const },
  { to: "/profiles", icon: "👤", label: "Profiles", module: null },
] as const;

const HIDDEN_NAV_PREFIXES = ["/admin"];

export default function AppShell() {
  const { pathname } = useLocation();
  const hideBottomNav = HIDDEN_NAV_PREFIXES.some((p) =>
    pathname.startsWith(p),
  );

  const householdName = useHouseholdStore((s) => s.householdName);
  const profiles = useHouseholdStore((s) => s.profiles);
  const fetchProfiles = useHouseholdStore((s) => s.fetchProfiles);
  const fetchHousehold = useHouseholdStore((s) => s.fetchHousehold);
  const profile = useAuthStore((s) => s.profile);
  const logout = useAuthStore((s) => s.logout);
  const { toasts, dismissToast, requestPermission } = useNotifications();
  const { modulesEnabled, privacyMode } = useHouseholdSettings();
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setShowProfileMenu(false);
      }
    }
    if (showProfileMenu) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [showProfileMenu]);

  // Filter nav items based on enabled modules
  const visibleNavItems = useMemo(
    () =>
      navItems.filter(
        (item) => item.module === null || modulesEnabled[item.module],
      ),
    [modulesEnabled],
  );

  useEffect(() => {
    requestPermission();
  }, [requestPermission]);

  useEffect(() => {
    if (profiles.length === 0) {
      fetchProfiles();
    }
    if (!householdName) {
      fetchHousehold();
    }
  }, [profiles.length, householdName, fetchProfiles, fetchHousehold]);

  return (
    <div className={`flex h-screen flex-col bg-gray-50 text-gray-900 dark:bg-gray-900 dark:text-gray-100 ${privacyMode ? "privacy-mode" : ""}`}>
      <NotificationToast toasts={toasts} onDismiss={dismissToast} />
      {/* Top bar */}
      <header className="flex shrink-0 items-center justify-between border-b border-gray-200 bg-white px-6 py-3 dark:border-gray-700 dark:bg-gray-800">
        <div className="flex items-center gap-4">
          <Link
            to="/"
            className="flex items-center gap-2 text-gray-800 transition-opacity hover:opacity-80 dark:text-gray-100"
            aria-label="Hestia home"
          >
            <HestiaLogo size={28} />
            <span className="text-lg font-semibold tracking-tight">Hestia</span>
          </Link>
          <span className="hidden h-6 w-px bg-gray-200 dark:bg-gray-700 sm:block" />
          <Clock />
          {householdName && (
            <span className="text-sm font-medium text-gray-500 dark:text-gray-400">
              {householdName}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {/* Profile switcher */}
          <div className="relative" ref={menuRef}>
            <button
              onClick={() => setShowProfileMenu(!showProfileMenu)}
              className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm text-gray-600 transition-colors hover:bg-gray-100 active:bg-gray-200 dark:text-gray-300 dark:hover:bg-gray-700 dark:active:bg-gray-600"
              aria-label="Switch profile"
            >
              <span className="text-lg">{profile?.avatar || "👤"}</span>
              <span className="max-w-[100px] truncate font-medium">{profile?.name || "Profile"}</span>
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
              </svg>
            </button>

            {showProfileMenu && (
              <div className="absolute right-0 top-full z-50 mt-1 w-48 overflow-hidden rounded-xl border border-gray-200 bg-white shadow-lg dark:border-gray-600 dark:bg-gray-800">
                <div className="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-gray-400">
                  Signed in as
                </div>
                <div className="border-b border-gray-100 px-3 pb-2 dark:border-gray-700">
                  <span className="font-medium text-gray-800 dark:text-gray-200">{profile?.name}</span>
                  <span className="ml-1.5 rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-500 dark:bg-gray-700 dark:text-gray-400">
                    {profile?.role}
                  </span>
                </div>
                <button
                  onClick={() => {
                    setShowProfileMenu(false);
                    logout();
                  }}
                  className="flex w-full items-center gap-2 px-3 py-2.5 text-left text-sm text-gray-700 transition-colors hover:bg-gray-50 active:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
                >
                  <span>🔄</span>
                  <span>Switch Profile</span>
                </button>
              </div>
            )}
          </div>

          <Link
            to="/admin"
            className="touch-target flex items-center justify-center rounded-lg p-2 text-gray-500 transition-colors hover:bg-gray-100 active:bg-gray-200 dark:text-gray-400 dark:hover:bg-gray-700 dark:active:bg-gray-600"
            aria-label="Settings"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-7 w-7"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
              />
            </svg>
          </Link>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>

      {/* Bottom navigation */}
      {!hideBottomNav && (
        <nav className="shrink-0 border-t border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
          <div className="flex items-stretch justify-around">
            {visibleNavItems.map(({ to, icon, label }) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  `touch-target flex flex-1 flex-col items-center justify-center gap-0.5 py-2 text-sm font-medium transition-colors ${
                    isActive
                      ? "text-[var(--color-accent)]"
                      : "text-gray-500 hover:text-gray-700 active:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200"
                  }`
                }
              >
                <span className="text-xl leading-none">{icon}</span>
                <span className="text-xs">{label}</span>
              </NavLink>
            ))}
          </div>
        </nav>
      )}
    </div>
  );
}
