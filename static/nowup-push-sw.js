self.addEventListener('push',event=>{
  let data={};try{data=event.data.json();}catch(_){}
  event.waitUntil(self.registration.showNotification(data.title||'NowUp',{body:data.body||'Abra seus pedidos para conferir.',tag:data.tag||'nowup',renotify:true,icon:'/static/nowup-push-192.png?v=100',badge:'/static/nowup-icon100.png?v=100',vibrate:[250,100,250],data:{url:data.url||'/painel'}}));
});
self.addEventListener('notificationclick',event=>{
  event.notification.close();let url;
  try{url=new URL(event.notification.data?.url||'/painel',self.location.origin);}catch(_){url=new URL('/painel',self.location.origin);}
  if(url.origin!==self.location.origin||!(url.pathname==='/painel'||url.pathname==='/cliente'||/^\/pedido\/[A-Za-z0-9_-]+$/.test(url.pathname)))url=new URL('/painel',self.location.origin);
  event.waitUntil(clients.openWindow(url.href));
});
