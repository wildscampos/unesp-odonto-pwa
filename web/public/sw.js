const CACHE_VERSION = "unesp-odonto-v4";
const BASE_PATH = "/unesp-odonto-pwa";
const APP_SHELL = [
  `${BASE_PATH}/`,
  `${BASE_PATH}/manifest.webmanifest`,
  `${BASE_PATH}/data/exams.json`,
  `${BASE_PATH}/icons/icon-192.png`,
  `${BASE_PATH}/icons/icon-512.png`
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_VERSION).then((cache) => cache.addAll(APP_SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_VERSION).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;

  if (request.mode === "navigate") {
    event.respondWith(fetch(request).catch(() => caches.match(`${BASE_PATH}/`)));
    return;
  }

  if (new URL(request.url).pathname === `${BASE_PATH}/data/exams.json`) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE_VERSION).then((cache) => cache.put(request, copy));
          return response;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  event.respondWith(caches.match(request).then((cached) => cached || fetch(request)));
});
