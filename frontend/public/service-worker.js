// Family Hub — Service Worker
// Implements offline-first caching with background sync replay.

const CACHE_VERSION = "v2";
const STATIC_CACHE = `family-hub-static-${CACHE_VERSION}`;
const API_CACHE = `family-hub-api-${CACHE_VERSION}`;
const QUEUE_DB_NAME = "family-hub-offline-queue";
const QUEUE_STORE = "requests";

// Mutating endpoints we should NEVER queue for replay — admin imports,
// backup operations, and auth flows would silently corrupt state if they
// landed late. Better to fail loudly while offline.
const NEVER_QUEUE_PREFIXES = ["/api/admin/", "/api/auth/"];

// Assets to pre-cache on install
const PRECACHE_URLS = ["/", "/index.html", "/manifest.json"];

// ── Install ─────────────────────────────────────────────────────────────────

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(STATIC_CACHE)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting()),
  );
});

// ── Activate ────────────────────────────────────────────────────────────────

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter(
              (key) =>
                key.startsWith("family-hub-") &&
                key !== STATIC_CACHE &&
                key !== API_CACHE,
            )
            .map((key) => caches.delete(key)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

// ── Fetch ───────────────────────────────────────────────────────────────────

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // API requests
  if (url.pathname.startsWith("/api/")) {
    if (request.method === "GET") {
      // Stale-while-revalidate for GET /api/*
      event.respondWith(staleWhileRevalidate(request));
    } else {
      // Queue mutating requests when offline
      event.respondWith(networkWithOfflineQueue(request));
    }
    return;
  }

  // Static assets — cache-first
  event.respondWith(cacheFirst(request));
});

// ── Strategies ──────────────────────────────────────────────────────────────

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    // Fallback to index.html for navigation requests (SPA)
    if (request.mode === "navigate") {
      return caches.match("/index.html");
    }
    return new Response("Offline", { status: 503 });
  }
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(API_CACHE);
  const cached = await cache.match(request);

  const fetchPromise = fetch(request)
    .then((response) => {
      if (response.ok) {
        cache.put(request, response.clone());
      }
      return response;
    })
    .catch(() => cached || new Response("{}", { status: 503 }));

  return cached || fetchPromise;
}

async function networkWithOfflineQueue(request) {
  const url = new URL(request.url);
  try {
    return await fetch(request);
  } catch {
    // Sensitive endpoints (admin import, auth) MUST NOT be silently
    // queued — replaying a stale auth token or replaying a destructive
    // restore would corrupt state. Surface the failure to the caller.
    if (NEVER_QUEUE_PREFIXES.some((p) => url.pathname.startsWith(p))) {
      return new Response(
        JSON.stringify({ detail: "Offline — please retry when reconnected." }),
        {
          status: 503,
          headers: { "Content-Type": "application/json" },
        },
      );
    }
    // Network unavailable — queue the request for replay
    await saveRequestToQueue(request);
    return new Response(JSON.stringify({ queued: true }), {
      status: 202,
      headers: { "Content-Type": "application/json" },
    });
  }
}

// ── IndexedDB Queue ─────────────────────────────────────────────────────────

function openQueueDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(QUEUE_DB_NAME, 1);
    req.onupgradeneeded = () => {
      req.result.createObjectStore(QUEUE_STORE, {
        keyPath: "id",
        autoIncrement: true,
      });
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function saveRequestToQueue(request) {
  const body = await request.clone().text();
  const db = await openQueueDB();
  const tx = db.transaction(QUEUE_STORE, "readwrite");
  tx.objectStore(QUEUE_STORE).add({
    url: request.url,
    method: request.method,
    headers: Object.fromEntries(request.headers.entries()),
    body,
    timestamp: Date.now(),
  });
  return new Promise((resolve, reject) => {
    tx.oncomplete = resolve;
    tx.onerror = () => reject(tx.error);
  });
}

async function replayQueuedRequests() {
  const db = await openQueueDB();
  const tx = db.transaction(QUEUE_STORE, "readonly");
  const store = tx.objectStore(QUEUE_STORE);

  const items = await new Promise((resolve, reject) => {
    const req = store.getAll();
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });

  for (const item of items) {
    try {
      await fetch(item.url, {
        method: item.method,
        headers: item.headers,
        body: item.method !== "GET" ? item.body : undefined,
      });
      // Remove from queue on success
      const delTx = db.transaction(QUEUE_STORE, "readwrite");
      delTx.objectStore(QUEUE_STORE).delete(item.id);
    } catch {
      // Still offline — leave in queue for next attempt
      break;
    }
  }
}

// ── Online event ────────────────────────────────────────────────────────────

self.addEventListener("message", (event) => {
  if (event.data === "REPLAY_QUEUE") {
    replayQueuedRequests();
  }
});
