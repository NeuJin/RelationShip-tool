// Service worker for For Our Relationship — handles web push notifications.

self.addEventListener('install', (e) => { self.skipWaiting(); });
self.addEventListener('activate', (e) => { e.waitUntil(self.clients.claim()); });

self.addEventListener('push', (event) => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch (e) { data = { body: event.data && event.data.text() }; }
  const title = data.title || 'For Our Relationship ❤️';
  const options = {
    body: data.body || 'Câu hỏi hôm nay đã sẵn sàng!',
    icon: '/static/icon-192.png',
    badge: '/static/icon-192.png',
    vibrate: [80, 40, 80],
    data: { url: data.url || '/' },
    tag: data.tag || 'four-daily',
    renotify: true,
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || '/';
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((list) => {
      for (const c of list) { if ('focus' in c) { c.navigate(url); return c.focus(); } }
      if (self.clients.openWindow) return self.clients.openWindow(url);
    })
  );
});
