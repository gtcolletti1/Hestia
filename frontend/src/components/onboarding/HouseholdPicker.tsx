import { useHouseholdStore } from "@/stores/householdStore";
import HestiaLogo from "@/components/shared/HestiaLogo";

export default function HouseholdPicker() {
  const households = useHouseholdStore((s) => s.discoveredHouseholds);
  const selectHousehold = useHouseholdStore((s) => s.selectHousehold);

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 p-6 dark:bg-gray-900">
      <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-xl dark:bg-gray-800">
        <div className="mb-6 flex justify-center">
          <HestiaLogo size={64} />
        </div>
        <h1 className="text-center text-2xl font-bold text-gray-900 dark:text-gray-100">
          Choose a household
        </h1>
        <p className="mt-1 text-center text-sm text-gray-500 dark:text-gray-400">
          This hub has more than one. Pick the one this device belongs to.
        </p>
        <ul className="mt-6 space-y-2">
          {households.map((h) => (
            <li key={h.id}>
              <button
                type="button"
                onClick={() => selectHousehold(h.id, h.name)}
                className="w-full rounded-xl border border-gray-200 bg-white px-4 py-4 text-left text-lg font-medium text-gray-900 transition-colors hover:border-blue-400 hover:bg-blue-50 active:scale-[0.99] dark:border-gray-700 dark:bg-gray-800 dark:text-gray-100 dark:hover:border-blue-500 dark:hover:bg-gray-700"
              >
                {h.name}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
