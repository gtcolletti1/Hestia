import { lazy, Suspense, useEffect } from "react";
import { Routes, Route } from "react-router-dom";
import AppShell from "@/components/layout/AppShell";
import KioskWrapper from "@/components/layout/KioskWrapper";
import LoadingSpinner from "@/components/shared/LoadingSpinner";
import SetupWizard from "@/components/onboarding/SetupWizard";
import ProfileSelector from "@/components/onboarding/ProfileSelector";
import HouseholdPicker from "@/components/onboarding/HouseholdPicker";
import { useHouseholdStore } from "@/stores/householdStore";
import { useAuthStore } from "@/stores/authStore";

const DashboardPage = lazy(() => import("@/pages/DashboardPage"));
const CalendarPage = lazy(() => import("@/pages/CalendarPage"));
const RoutinesPage = lazy(() => import("@/pages/RoutinesPage"));
const ListsPage = lazy(() => import("@/pages/ListsPage"));
const MealsPage = lazy(() => import("@/pages/MealsPage"));
const ProfilesPage = lazy(() => import("@/pages/ProfilesPage"));
const AdminPage = lazy(() => import("@/pages/AdminPage"));
const MessagesPage = lazy(() => import("@/pages/MessagesPage"));
const RewardsPage = lazy(() => import("@/pages/RewardsPage"));

export default function App() {
  const householdId = useHouseholdStore((s) => s.householdId);
  const profiles = useHouseholdStore((s) => s.profiles);
  const fetchProfiles = useHouseholdStore((s) => s.fetchProfiles);
  const bootStatus = useHouseholdStore((s) => s.bootStatus);
  const discover = useHouseholdStore((s) => s.discover);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  // Single-household appliance: ask the server who exists before deciding
  // whether to show the setup wizard, the household picker, or sign-in.
  // Without this, a fresh browser would fall straight through to the
  // wizard and create yet another duplicate household. discover() handles
  // its own error reporting via bootStatus = "error".
  useEffect(() => {
    void discover();
  }, [discover]);

  useEffect(() => {
    if (householdId && profiles.length === 0) {
      fetchProfiles();
    }
  }, [householdId, profiles.length, fetchProfiles]);

  const renderContent = () => {
    if (bootStatus === "checking") {
      return <LoadingSpinner message="Loading…" />;
    }

    if (bootStatus === "error") {
      return (
        <div className="flex min-h-screen items-center justify-center bg-gray-50 p-6 dark:bg-gray-900">
          <div className="w-full max-w-md rounded-2xl bg-white p-8 text-center shadow-xl dark:bg-gray-800">
            <div className="text-5xl">⚠️</div>
            <h1 className="mt-4 text-xl font-semibold text-gray-900 dark:text-gray-100">
              Can&apos;t reach the hub
            </h1>
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
              Check that the backend is running on this network and try again.
            </p>
            <button
              onClick={() => void discover()}
              className="mt-6 w-full rounded-xl bg-blue-500 px-6 py-4 text-lg font-semibold text-white transition-colors hover:bg-blue-600 active:scale-[0.98]"
            >
              Retry
            </button>
          </div>
        </div>
      );
    }

    if (bootStatus === "needs-setup") {
      return <SetupWizard />;
    }

    if (bootStatus === "needs-pick") {
      return <HouseholdPicker />;
    }

    if (!isAuthenticated) {
      return <ProfileSelector />;
    }

    return (
      <Suspense fallback={<LoadingSpinner message="Loading…" />}>
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={<DashboardPage />} />
            <Route path="calendar" element={<CalendarPage />} />
            <Route path="routines" element={<RoutinesPage />} />
            <Route path="lists" element={<ListsPage />} />
            <Route path="meals" element={<MealsPage />} />
            <Route path="profiles" element={<ProfilesPage />} />
            <Route path="messages" element={<MessagesPage />} />
            <Route path="rewards" element={<RewardsPage />} />
            <Route path="admin" element={<AdminPage />} />
          </Route>
        </Routes>
      </Suspense>
    );
  };

  // Single top-level KioskWrapper so the screensaver overlay (and its
  // auto-logout side effect) survives the re-renders triggered by login,
  // logout, and boot-state transitions.
  return <KioskWrapper>{renderContent()}</KioskWrapper>;
}
