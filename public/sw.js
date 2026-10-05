const CACHE = "te-shell-v2";
const ESTATICOS = "te-static-v1";

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.add("/offline.html")));
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE && k !== ESTATICOS).map((k) => caches.delete(k)))),
  );
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;

  // Páginas: sempre da rede; sem internet, mostra a tela offline
  if (req.mode === "navigate") {
    e.respondWith(fetch(req).catch(() => caches.match("/offline.html")));
    return;
  }

  // Arquivos estáticos do app (nomes com hash) e ícones: cache primeiro, abre mais rápido no celular
  const url = new URL(req.url);
  if (url.origin === self.location.origin && (url.pathname.startsWith("/_next/static/") || url.pathname.startsWith("/icons/"))) {
    e.respondWith(
      caches.open(ESTATICOS).then(async (cache) => {
        const guardado = await cache.match(req);
        if (guardado) return guardado;
        const resposta = await fetch(req);
        if (resposta.ok) cache.put(req, resposta.clone());
        return resposta;
      }),
    );
  }
});

// Toque na notificação: abre (ou volta para) o app na tela indicada
self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const url = (e.notification.data && e.notification.data.url) || "/";
  e.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((lista) => {
      for (const c of lista) {
        if ("focus" in c) {
          return (c.navigate ? c.navigate(url) : Promise.resolve(c)).then((w) => (w || c).focus());
        }
      }
      return self.clients.openWindow(url);
    }),
  );
});