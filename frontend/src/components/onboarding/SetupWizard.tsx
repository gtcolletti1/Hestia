import { useState } from "react";
import { households, profiles as profilesApi, auth } from "@/api/endpoints";
import client from "@/api/client";
import { useHouseholdStore } from "@/stores/householdStore";
import { useAuthStore } from "@/stores/authStore";
import HestiaLogo from "@/components/shared/HestiaLogo";

const PRESET_COLORS = [
  "#EF4444", "#F97316", "#F59E0B", "#EAB308",
  "#84CC16", "#22C55E", "#14B8A6", "#06B6D4",
  "#3B82F6", "#6366F1", "#8B5CF6", "#A855F7",
  "#D946EF", "#EC4899", "#F43F5E", "#78716C",
];

export default function SetupWizard() {
  const [step, setStep] = useState(1);
  const [householdName, setHouseholdName] = useState("");
  const [householdId, setHouseholdId] = useState("");
  const [profileName, setProfileName] = useState("");
  const [profileColor, setProfileColor] = useState(PRESET_COLORS[8]);
  const [pin, setPin] = useState("");
  const [pinConfirm, setPinConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const store = useHouseholdStore();
  const authStore = useAuthStore();

  const createHousehold = async () => {
    if (!householdName.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const { data } = await households.create({ name: householdName.trim() });
      setHouseholdId(data.id);
      setStep(2);
    } catch (e: unknown) {
      // 409 means another browser/tab already created the household between
      // our discover() call and the create — back off and re-run discovery
      // so the user lands on ProfileSelector instead of being stuck.
      const status = (e as { response?: { status?: number } })?.response?.status;
      if (status === 409) {
        await store.discover();
        return;
      }
      setError("Failed to create household. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const validatePin = (value: string): string | null => {
    if (!/^\d+$/.test(value)) return "PIN must contain only digits.";
    if (value.length < 4 || value.length > 12) return "PIN must be 4-12 digits.";
    return null;
  };

  const createProfile = async () => {
    if (!profileName.trim()) return;
    const pinError = validatePin(pin);
    if (pinError) {
      setError(pinError);
      return;
    }
    if (pin !== pinConfirm) {
      setError("PINs do not match.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const { data: profile } = await profilesApi.create({
        name: profileName.trim(),
        color: profileColor,
        role: "admin",
        household_id: householdId,
        pin,
      });
      const { data: loginData } = await auth.login({
        profile_id: profile.id,
        pin,
      });
      authStore.login(loginData.access_token, loginData.profile);
      setStep(3);
    } catch {
      setError("Failed to create profile. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const seedData = async () => {
    setLoading(true);
    setError(null);
    try {
      await client.post("/seed", { household_id: householdId });
      setStep(4);
    } catch {
      setError("Failed to seed data. You can skip this step.");
    } finally {
      setLoading(false);
    }
  };

  const finish = () => {
    store.selectHousehold(householdId, householdName);
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 p-6 dark:bg-gray-900">
      <div className="w-full max-w-lg rounded-2xl bg-white p-8 shadow-xl dark:bg-gray-800">
        {/* Progress dots */}
        <div className="mb-8 flex items-center justify-center gap-2">
          {[1, 2, 3, 4].map((s) => (
            <div
              key={s}
              className={`h-2.5 w-2.5 rounded-full transition-colors ${
                s <= step
                  ? "bg-blue-500"
                  : "bg-gray-300 dark:bg-gray-600"
              }`}
            />
          ))}
        </div>

        {error && (
          <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
            {error}
          </div>
        )}

        {/* Step 1: Create household */}
        {step === 1 && (
          <div className="space-y-6 text-center">
            <div className="flex justify-center">
              <HestiaLogo size={64} />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                Welcome to Hestia
              </h1>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                A private, local home hub for busy families.
              </p>
            </div>
            <p className="text-gray-500 dark:text-gray-400">
              Let&apos;s set up your household to get started.
            </p>
            <input
              type="text"
              placeholder="Household name (e.g. The Smiths)"
              value={householdName}
              onChange={(e) => setHouseholdName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && createHousehold()}
              className="w-full rounded-xl border border-gray-300 px-4 py-4 text-lg focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              autoFocus
            />
            <button
              onClick={createHousehold}
              disabled={loading || !householdName.trim()}
              className="w-full rounded-xl bg-blue-500 px-6 py-4 text-lg font-semibold text-white transition-colors hover:bg-blue-600 active:scale-[0.98] disabled:opacity-50"
            >
              {loading ? "Creating…" : "Create Household"}
            </button>
          </div>
        )}

        {/* Step 2: Create profile */}
        {step === 2 && (
          <div className="space-y-6 text-center">
            <div className="text-5xl">👤</div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              Create your profile
            </h1>
            <p className="text-gray-500 dark:text-gray-400">
              This will be your admin profile.
            </p>
            <input
              type="text"
              placeholder="Your name"
              value={profileName}
              onChange={(e) => setProfileName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && createProfile()}
              className="w-full rounded-xl border border-gray-300 px-4 py-4 text-lg focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              autoFocus
            />
            <div>
              <p className="mb-2 text-sm font-medium text-gray-500 dark:text-gray-400">
                Pick a color
              </p>
              <div className="grid grid-cols-8 gap-2 justify-items-center">
                {PRESET_COLORS.map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setProfileColor(c)}
                    className={`h-10 w-10 rounded-full transition-transform ${
                      profileColor === c
                        ? "scale-125 ring-2 ring-offset-2 ring-blue-500 dark:ring-offset-gray-800"
                        : "hover:scale-110"
                    }`}
                    style={{ backgroundColor: c }}
                    aria-label={c}
                  />
                ))}
              </div>
            </div>
            <div className="space-y-2 text-left">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Set a PIN (4-12 digits)
              </p>
              <p className="text-xs text-gray-400 dark:text-gray-500">
                Admins must use a PIN to sign in. You can change it later in
                Settings.
              </p>
              <input
                type="password"
                inputMode="numeric"
                autoComplete="new-password"
                placeholder="PIN"
                value={pin}
                onChange={(e) => setPin(e.target.value.replace(/\D/g, "").slice(0, 12))}
                className="w-full rounded-xl border border-gray-300 px-4 py-4 text-lg tracking-[0.4em] focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              />
              <input
                type="password"
                inputMode="numeric"
                autoComplete="new-password"
                placeholder="Confirm PIN"
                value={pinConfirm}
                onChange={(e) =>
                  setPinConfirm(e.target.value.replace(/\D/g, "").slice(0, 12))
                }
                onKeyDown={(e) => e.key === "Enter" && createProfile()}
                className="w-full rounded-xl border border-gray-300 px-4 py-4 text-lg tracking-[0.4em] focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              />
            </div>
            <button
              onClick={createProfile}
              disabled={
                loading ||
                !profileName.trim() ||
                pin.length < 4 ||
                pin !== pinConfirm
              }
              className="w-full rounded-xl bg-blue-500 px-6 py-4 text-lg font-semibold text-white transition-colors hover:bg-blue-600 active:scale-[0.98] disabled:opacity-50"
            >
              {loading ? "Creating…" : "Create Profile"}
            </button>
          </div>
        )}

        {/* Step 3: Seed sample data */}
        {step === 3 && (
          <div className="space-y-6 text-center">
            <div className="text-5xl">📦</div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              Seed sample data?
            </h1>
            <p className="text-gray-500 dark:text-gray-400">
              We can add sample events, routines, lists, and meals so you
              can try things out right away.
            </p>
            <button
              onClick={seedData}
              disabled={loading}
              className="w-full rounded-xl bg-blue-500 px-6 py-4 text-lg font-semibold text-white transition-colors hover:bg-blue-600 active:scale-[0.98] disabled:opacity-50"
            >
              {loading ? "Seeding…" : "Add sample data so I can try things out"}
            </button>
            <button
              onClick={() => setStep(4)}
              disabled={loading}
              className="w-full rounded-xl border border-gray-300 px-6 py-4 text-lg font-medium text-gray-600 transition-colors hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
            >
              Skip
            </button>
          </div>
        )}

        {/* Step 4: All set */}
        {step === 4 && (
          <div className="space-y-6 text-center">
            <div className="text-5xl">🎉</div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              You&apos;re all set!
            </h1>
            <p className="text-gray-500 dark:text-gray-400">
              Your household is ready. Let&apos;s head to the dashboard.
            </p>
            <button
              onClick={finish}
              className="w-full rounded-xl bg-blue-500 px-6 py-4 text-lg font-semibold text-white transition-colors hover:bg-blue-600 active:scale-[0.98]"
            >
              Go to Dashboard
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
