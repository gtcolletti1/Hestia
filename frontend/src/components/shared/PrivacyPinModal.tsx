import { useEffect, useRef, useState } from "react";
import { auth } from "@/api/endpoints";
import { usePrivacyRevealStore } from "@/stores/privacyRevealStore";

interface Props {
  onClose: () => void;
}

/** Modal that asks for a household member's PIN and, on success, unlocks
 *  the privacy-reveal window. Used to gate access to event details, meal
 *  names, etc. when privacy mode is enabled. */
export default function PrivacyPinModal({ onClose }: Props) {
  const [pin, setPin] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const reveal = usePrivacyRevealStore((s) => s.reveal);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  async function submit() {
    if (!pin || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      await auth.verifyPin(pin);
      reveal();
      onClose();
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      setError(status === 401 ? "Incorrect PIN. Please try again." : "Could not verify PIN. Please try again.");
      setPin("");
      inputRef.current?.focus();
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 p-6"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Enter PIN to reveal details"
    >
      <div
        className="w-full max-w-sm rounded-2xl bg-white p-8 shadow-xl dark:bg-gray-800 text-center space-y-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div>
          <div className="mx-auto h-14 w-14 rounded-full bg-blue-100 dark:bg-blue-900/40 flex items-center justify-center text-3xl">
            🔒
          </div>
          <h2 className="mt-4 text-xl font-bold text-gray-900 dark:text-gray-100">
            Reveal Details
          </h2>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Enter any household member's PIN to unlock for 5 minutes.
          </p>
        </div>

        {error && (
          <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
            {error}
          </div>
        )}

        <input
          ref={inputRef}
          type="password"
          inputMode="numeric"
          maxLength={8}
          placeholder="PIN"
          value={pin}
          onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          className="w-full rounded-xl border border-gray-300 px-4 py-4 text-center text-2xl tracking-[0.5em] focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
        />

        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 min-h-[44px] rounded-xl border border-gray-300 px-4 py-3 font-medium text-gray-600 dark:border-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={submitting || !pin}
            className="flex-1 min-h-[44px] rounded-xl bg-blue-500 px-4 py-3 font-semibold text-white disabled:opacity-50 hover:bg-blue-600"
          >
            {submitting ? "…" : "Reveal"}
          </button>
        </div>
      </div>
    </div>
  );
}
