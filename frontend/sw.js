/**
 * =============================================================
 *   PetFeeder IoT — Service Worker
 *   Enables offline support & PWA installability
 * =============================================================
 */

const CACHE_NAME = "petfeeder-v1.0.0";
const STATIC_ASSETS = [
    "/",
    "/index.html",
    "/style.css",
    "/app.js",
    "/manifest.json",
    "/icons/icon-192.png",
    "/icons/icon-512.png",
];

// ── Install: cache all static assets ──────────────────────────
self.addEventListener("install", (event) => {
    console.log("[SW] Installing service worker...");
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log("[SW] Caching static assets");
            return cache.addAll(STATIC_ASSETS).catch((err) => {
                console.warn("[SW] Some assets failed to cache:", err);
            });
        })
    );
    self.skipWaiting();
});

// ── Activate: clean old caches ────────────────────────────────
self.addEventListener("activate", (event) => {
    console.log("[SW] Activating service worker...");
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(
                keys
                    .filter((key) => key !== CACHE_NAME)
                    .map((key) => {
                        console.log("[SW] Deleting old cache:", key);
                        return caches.delete(key);
                    })
            )
        )
    );
    self.clients.claim();
});

// ── Fetch: Network-first for API, Cache-first for static ──────
self.addEventListener("fetch", (event) => {
    const url = new URL(event.request.url);

    // API calls — harus online, jangan di-cache
    if (url.pathname.startsWith("/api/") || url.hostname === "localhost") {
        event.respondWith(
            fetch(event.request).catch(() => {
                return new Response(
                    JSON.stringify({
                        error: "Offline",
                        message: "Tidak ada koneksi ke server. Pastikan backend berjalan.",
                    }),
                    {
                        status: 503,
                        headers: { "Content-Type": "application/json" },
                    }
                );
            })
        );
        return;
    }

    // Static assets — Cache first, fallback to network
    event.respondWith(
        caches.match(event.request).then((cached) => {
            if (cached) return cached;
            return fetch(event.request).then((response) => {
                // Cache baru untuk static files
                if (response.ok && event.request.method === "GET") {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
                }
                return response;
            });
        })
    );
});

// ── Push Notifications (untuk future: feeding alerts) ─────────
self.addEventListener("push", (event) => {
    const data = event.data?.json() || {};
    const title = data.title || "PetFeeder IoT";
    const body = data.body || "Ada notifikasi dari perangkat";
    const options = {
        body,
        icon: "/icons/icon-192.png",
        badge: "/icons/icon-192.png",
        vibrate: [200, 100, 200],
        data: data,
    };
    event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
    event.notification.close();
    event.waitUntil(clients.openWindow("/"));
});
