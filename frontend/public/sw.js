/* C2D2 Service Worker — satisfies PWA install criteria + caches app shell for offline evaluate */
const CACHE = "c2d2-v2";

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then(clientList => {
      if (clientList.length > 0) return clientList[0].focus();
      return clients.openWindow("/battlespace");
    }),
  );
});

self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // Never intercept cross-origin requests (API at localhost:8000).
  // SW re-fetching them strips CORS context and causes browser CORS errors.
  // The offline queue in api.ts handles failures independently.
  if (url.origin !== self.location.origin) {
    return;
  }

  // Next.js static chunks: content-hashed, cache forever
  if (url.pathname.startsWith("/_next/static/")) {
    event.respondWith(
      caches.match(event.request).then(hit =>
        hit || fetch(event.request).then(res => {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(event.request, clone));
          return res;
        })
      )
    );
    return;
  }

  // Navigation (HTML pages): network first, cache fallback
  if (event.request.mode === "navigate") {
    event.respondWith(
      fetch(event.request)
        .then(res => {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(event.request, clone));
          return res;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  event.respondWith(fetch(event.request));
});
