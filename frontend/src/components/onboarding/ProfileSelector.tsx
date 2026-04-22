import { useState } from "react";
import { auth } from "@/api/endpoints";
import { useHouseholdStore } from "@/stores/householdStore";
import { useAuthStore } from "@/stores/authStore";
import HestiaLogo from "@/components/shared/HestiaLogo";
import type { Profile } from "@/types";

export default function ProfileSelector() {
  const householdId = useHouseholdStore((s) => s.householdId);
  const householdName = useHouseholdStore((s) => s.householdName);
  const storeProfiles = useHouseholdStore((s) => s.profiles);
  const fetchProfiles = useHouseholdStore((s) => s.fetchProfiles);
  const authStore = useAuthStore();

  const [pin, setPin] = useState("");
  const [selectedProfile, setSelectedProfile] = useState<Profile | null>(null);
  const [needsPin, setNeedsPin] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch profiles on first render if needed
  if (householdId && storeProfiles.length === 0) {
    fetchProfiles();
  }

  const handleProfileTap = async (profile: Profile) => {
    setError(null);
    setSelectedProfile(profile);
    setLoading(true);

    try {
      // Try login without PIN first (works if no PIN is set)
      const { data } = await auth.login({ profile_id: profile.id, pin: "" });
      authStore.login(data.access_token, data.profile);
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 401) {
        // PIN is required
        setNeedsPin(true);
        setLoading(false);
        return;
      }
      setError("Failed to log in. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handlePinSubmit = async () => {
    if (!selectedProfile || !pin) return;
    setLoading(true);
    setError(null);

    try {
      const { data } = await auth.login({ profile_id: selectedProfile.id, pin });
      authStore.login(data.access_token, data.profile);
    } catch {
      setError("Incorrect PIN. Please try again.");
      setPin("");
    } finally {
      setLoading(false);
    }
  };

  if (needsPin && selectedProfile) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 p-6 dark:bg-gray-900">
        <div className="w-full max-w-sm rounded-2xl bg-white p-8 shadow-xl dark:bg-gray-800 text-center space-y-6">
          <div
            className="mx-auto flex h-20 w-20 items-center justify-center rounded-full text-3xl font-bold text-white"
            style={{ backgroundColor: selectedProfile.color }}
          >
            {selectedProfile.name[0]}
          </div>
          <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
            Enter PIN for {selectedProfile.name}
          </h2>
          {error && (
            <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
              {error}
            </div>
          )}
          <input
            type="password"
            inputMode="numeric"
            maxLength={8}
            placeholder="PIN"
            value={pin}
            onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))}
            onKeyDown={(e) => e.key === "Enter" && handlePinSubmit()}
            className="w-full rounded-xl border border-gray-300 px-4 py-4 text-center text-2xl tracking-[0.5em] focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            autoFocus
          />
          <div className="flex gap-3">
            <button
              onClick={() => {
                setNeedsPin(false);
                setSelectedProfile(null);
                setPin("");
                setError(null);
              }}
              className="flex-1 rounded-xl border border-gray-300 px-4 py-3 font-medium text-gray-600 dark:border-gray-600 dark:text-gray-300"
            >
              Back
            </button>
            <button
              onClick={handlePinSubmit}
              disabled={loading || !pin}
              className="flex-1 rounded-xl bg-blue-500 px-4 py-3 font-semibold text-white disabled:opacity-50"
            >
              {loading ? "…" : "Enter"}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 p-6 dark:bg-gray-900">
      <div className="w-full max-w-lg rounded-2xl bg-white p-8 shadow-xl dark:bg-gray-800 text-center space-y-6">
        <div className="flex justify-center">
          <HestiaLogo size={56} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            {householdName || "Hestia"}
          </h1>
        </div>
        <p className="text-gray-500 dark:text-gray-400">Who&apos;s here?</p>
        {error && (
          <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
            {error}
          </div>
        )}
        <div className="grid grid-cols-2 gap-4">
          {storeProfiles.map((profile) => (
            <button
              key={profile.id}
              onClick={() => handleProfileTap(profile)}
              disabled={loading}
              className="flex flex-col items-center gap-2 rounded-xl border border-gray-200 p-6 transition-all hover:border-blue-400 hover:shadow-md active:scale-95 disabled:opacity-50 dark:border-gray-600 dark:hover:border-blue-500"
            >
              <div
                className="flex h-16 w-16 items-center justify-center rounded-full text-2xl font-bold text-white"
                style={{ backgroundColor: profile.color }}
              >
                {profile.name[0]}
              </div>
              <span className="text-lg font-medium text-gray-900 dark:text-gray-100">
                {profile.name}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
