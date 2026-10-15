self.addEventListener('push',event=>{
  let data={};try{data=event.data.json();}catch(_){}
  event.waitUntil(self.registration.showNotification(data.title||'NowUp',{body:data.body||'Abra seus pedidos para conferir.',tag:data.tag||'nowup',renotify:true,icon:'/static/nowup-push-192.png?v=183',badge:'/static/nowup-icon100.png?v=183',vibrate:[250,100,250],data:{url:data.url||'/painel'}}));
});
self.addEventListener('notificationclick',event=>{
  event.notification.close();let url;
  try{url=new URL(event.notification.data?.url||'/painel',self.location.origin);}catch(_){url=new URL('/painel',self.location.origin);}
  if(url.origin!==self.location.origin||!(url.pathname==='/painel'||url.pathname==='/cliente'||/^\/pedido\/[A-Za-z0-9_-]+$/.test(url.pathname)))url=new URL('/painel',self.location.origin);
  event.waitUntil(clients.openWindow(url.href));
});

// V182: use the SAME worker as order notifications. No offline order queue,
// no caching of login, pages, APIs, cart or personal data.
self.addEventListener('install', event => { event.waitUntil(self.skipWaiting()); });
self.addEventListener('activate', event => { event.waitUntil(self.clients.claim()); });
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET' || event.request.mode !== 'navigate') return;
  event.respondWith(fetch(event.request, {cache: 'no-store'}).catch(() => new Response(
    '<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NowUp — sem conexão</title><body style="font-family:system-ui;background:white;color:#263247;padding:32px"><h1>Você está sem conexão</h1><p>Conecte-se à internet para acessar o NowUp e conferir seus pedidos.</p><p>Nenhum pedido é enviado por esta tela.</p><button onclick="location.reload()" style="padding:14px">Tentar novamente</button></body></html>',
    {status: 503, headers: {'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store'}}
  )));
});
