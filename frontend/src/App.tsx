import { lazy, Suspense, useEffect } from "react";
import { Routes, Route } from "react-router-dom";
import AppShell from "@/components/layout/AppShell";
import KioskWrapper from "@/components/layout/KioskWrapper";
import LoadingSpinner from "@/components/shared/LoadingSpinner";
import SetupWizard from "@/components/onboarding/SetupWizard";
import ProfileSelector from "@/components/onboarding/ProfileSelector";
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

export default function App() {
  const householdId = useHouseholdStore((s) => s.householdId);
  const profiles = useHouseholdStore((s) => s.profiles);
  const fetchProfiles = useHouseholdStore((s) => s.fetchProfiles);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  useEffect(() => {
    if (householdId && profiles.length === 0) {
      fetchProfiles();
    }
  }, [householdId, profiles.length, fetchProfiles]);

  // No household yet → show setup wizard
  if (!householdId) {
    return (
      <KioskWrapper>
        <SetupWizard />
      </KioskWrapper>
    );
  }

  // Household exists but not logged in → show profile selector
  if (!isAuthenticated) {
    return (
      <KioskWrapper>
        <ProfileSelector />
      </KioskWrapper>
    );
  }

  return (
    <KioskWrapper>
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
            <Route path="admin" element={<AdminPage />} />
          </Route>
        </Routes>
      </Suspense>
    </KioskWrapper>
  );
}
