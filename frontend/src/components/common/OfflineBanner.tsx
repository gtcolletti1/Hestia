import { useEffect, useState } from "react";
import { isOnline, onOnlineStatusChange } from "@/utils/offline";

/**
 * Slim banner pinned to the top of the viewport while the device has lost
 * its network connection. The service worker keeps serving cached data, so
 * the dashboard stays usable; the banner just makes it obvious that what's
 * showing may be stale and that mutations will be queued / dropped.
 */
export default function OfflineBanner() {
  const [online, setOnline] = useState(() => isOnline());

  useEffect(() => onOnlineStatusChange(setOnline), []);

  if (online) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed inset-x-0 top-0 z-[100] flex items-center justify-center gap-2 bg-amber-500 px-4 py-1.5 text-center text-xs font-medium text-amber-950 shadow-md"
    >
      <span aria-hidden>📡</span>
      <span>
        Offline — showing the last data we received. Changes will be saved when
        we reconnect.
      </span>
    </div>
  );
}
