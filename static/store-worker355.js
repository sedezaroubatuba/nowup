// Online-only catalogue worker, confined to this store. Never queue orders.
self.addEventListener('install', event => event.waitUntil(self.skipWaiting()));
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET' || event.request.mode !== 'navigate' ||
      url.origin !== self.location.origin || !url.pathname.startsWith(STORE_SCOPE)) return;
  event.respondWith(fetch(event.request, {cache: 'no-store'}).catch(() => new Response(
    '<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Sem conexão</title><body style="font-family:system-ui;padding:24px"><h1>Você está sem conexão</h1><p>Conecte-se à internet para acessar o cardápio. Nenhum pedido foi enviado por esta tela.</p><button onclick="location.reload()">Tentar novamente</button></body></html>',
    {status: 503, headers: {'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store'}}
  )));
});
self.addEventListener('push', event => {
  let data = {}; try { const value=event.data.json();if(value&&typeof value==='object'&&!Array.isArray(value))data=value; } catch (_) {}
  event.waitUntil(self.registration.showNotification(data.title || STORE_NAME, {
    body: data.body || 'Confira seus pedidos nesta loja.',
    icon: STORE_SCOPE + 'app-icon/192.png', badge:'/static/nowup-push-badge375.svg', tag:String(data.tag||('nowup-'+(data.eventId||'aviso'))), renotify:false, data: {url: data.url}
  }));
});
self.addEventListener('notificationclick', event => {
  event.notification.close();
  let url;
  try { url = new URL(event.notification.data?.url || STORE_SCOPE + 'pedidos', self.location.origin); }
  catch (_) { url = new URL(STORE_SCOPE + 'pedidos', self.location.origin); }
  if (url.origin !== self.location.origin || url.username || url.password || !url.pathname.startsWith(STORE_SCOPE))
    url = new URL(STORE_SCOPE + 'pedidos', self.location.origin);
  event.waitUntil(clients.openWindow(url.href));
});
