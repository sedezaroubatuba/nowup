self.addEventListener('push', event => {
  let data = {};
  try { data = event.data.json(); } catch (_) {}
  event.waitUntil(self.registration.showNotification(data.title || 'NowUp', {
    body: data.body || 'Abra o painel para conferir seus pedidos.',
    tag: data.tag || 'nowup', data: {url: data.url || '/painel'}
  }));
});
self.addEventListener('notificationclick', event => {
  event.notification.close();
  let url = new URL(event.notification.data?.url || '/painel', self.location.origin);
  if (url.origin !== self.location.origin || url.pathname !== '/painel') url = new URL('/painel', self.location.origin);
  event.waitUntil(clients.openWindow(url.href));
});
