// System-tray notices: role-safe links, stable event tags and NowUp branding.
self.addEventListener('push',event=>{
  let data={};try{const value=event.data.json();if(value&&typeof value==='object'&&!Array.isArray(value))data=value}catch(_){}
  let title=typeof data.title==='string'?data.title.slice(0,120):'NowUp';
  if(!/nowup/i.test(title))title='NowUp · '+title;
  event.waitUntil(self.registration.showNotification(title,{body:typeof data.body==='string'?data.body.slice(0,600):'Abra o NowUp para conferir.',tag:String(data.tag||('nowup-'+(data.eventId||'aviso'))),renotify:false,icon:'/static/nowup-notice-logo374.png',badge:'/static/nowup-push-badge375.svg',vibrate:[250,100,250],data:{url:data.url||'/app'}}));
});
self.addEventListener('notificationclick',event=>{
  event.notification.close();let url;
  try{url=new URL(event.notification.data?.url||'/app',self.location.origin)}catch(_){url=new URL('/app',self.location.origin)}
  const valid=url.origin===self.location.origin&&!url.username&&!url.password&&(url.pathname==='/app'||url.pathname==='/painel'||url.pathname==='/cliente'||url.pathname==='/suporte'||/^\/pedido\/[A-Za-z0-9_-]+$/.test(url.pathname)||/^\/p\/[A-Za-z0-9_-]+\/(pedido\/[A-Za-z0-9_-]+|pedidos|suporte)$/.test(url.pathname));
  if(!valid)url=new URL('/app',self.location.origin);
  event.waitUntil((async()=>{if(clients.matchAll){const windows=await clients.matchAll({type:'window',includeUncontrolled:true});for(const client of windows){try{const current=new URL(client.url);const scope=path=>(/^\/p\/([^/]+)\//.exec(path)||[])[1]||'';if(current.origin===url.origin&&scope(current.pathname)===scope(url.pathname)&&client.navigate&&client.focus){const moved=await client.navigate(url.href);if(moved)return await client.focus()}}catch(_){}}}return clients.openWindow(url.href)})());
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
