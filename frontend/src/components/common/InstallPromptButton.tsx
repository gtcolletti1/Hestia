import { useEffect, useState } from "react";

/**
 * The browser will fire `beforeinstallprompt` only on PWA-capable contexts
 * (HTTPS or localhost, manifest + SW present, not already installed). We
 * stash the event so the user can trigger Install on demand from a normal
 * button — Chrome / Edge no longer auto-prompt.
 *
 * If the event never fires (Safari / iOS, already installed, no SW) the
 * component renders nothing.
 */

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

export default function InstallPromptButton() {
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(
    null,
  );
  const [installed, setInstalled] = useState(false);

  useEffect(() => {
    const onPrompt = (e: Event) => {
      e.preventDefault();
      setDeferred(e as BeforeInstallPromptEvent);
    };
    const onInstalled = () => {
      setInstalled(true);
      setDeferred(null);
    };
    window.addEventListener("beforeinstallprompt", onPrompt);
    window.addEventListener("appinstalled", onInstalled);
    return () => {
      window.removeEventListener("beforeinstallprompt", onPrompt);
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, []);

  if (installed) {
    return (
      <p className="text-xs text-gray-500 dark:text-gray-400">
        ✓ Hestia is installed on this device.
      </p>
    );
  }

  if (!deferred) return null;

  const handleInstall = async () => {
    await deferred.prompt();
    const choice = await deferred.userChoice;
    if (choice.outcome === "accepted") {
      setDeferred(null);
    }
  };

  return (
    <button
      type="button"
      onClick={handleInstall}
      className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
    >
      📲 Install Hestia on this device
    </button>
  );
}
