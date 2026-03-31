type OnlineCallback = (online: boolean) => void;

const listeners: Set<OnlineCallback> = new Set();
let currentOnline = typeof navigator !== "undefined" ? navigator.onLine : true;

function handleOnline() {
  currentOnline = true;
  listeners.forEach((cb) => cb(true));

  // Tell the service worker to replay queued requests
  if (navigator.serviceWorker?.controller) {
    navigator.serviceWorker.controller.postMessage("REPLAY_QUEUE");
  }
}

function handleOffline() {
  currentOnline = false;
  listeners.forEach((cb) => cb(false));
}

if (typeof window !== "undefined") {
  window.addEventListener("online", handleOnline);
  window.addEventListener("offline", handleOffline);
}

/**
 * Returns the current online/offline status.
 */
export function isOnline(): boolean {
  return currentOnline;
}

/**
 * Subscribe to online/offline status changes.
 * Returns an unsubscribe function.
 */
export function onOnlineStatusChange(callback: OnlineCallback): () => void {
  listeners.add(callback);
  return () => {
    listeners.delete(callback);
  };
}

/**
 * Register the service worker for offline-first caching.
 */
export async function registerServiceWorker(): Promise<void> {
  if (!("serviceWorker" in navigator)) {
    console.log("Service workers not supported");
    return;
  }

  try {
    const registration = await navigator.serviceWorker.register(
      "/service-worker.js",
      { scope: "/" },
    );
    console.log("SW registered:", registration.scope);
  } catch (error) {
    console.error("SW registration failed:", error);
  }
}

/**
 * Unregister the active service worker.
 */
export function unregisterServiceWorker(): void {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.ready.then((registration) => {
      registration.unregister();
    });
  }
}
