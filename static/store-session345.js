/* Keep order chat, receipts and status requests inside this store's session. */
(()=>{'use strict';
 const node=document.getElementById('store-app256');if(!node)return;
 const store=JSON.parse(node.textContent),prefix='/p/'+encodeURIComponent(store.slug);
 function scoped(value){
  const url=new URL(value,location.href);
  if(url.origin===location.origin&&(/^\/pedidos?\//.test(url.pathname)||url.pathname==='/avisos203'||url.pathname==='/cliente/pedidos/resumo202'||url.pathname==='/cliente/avisos'||url.pathname==='/cliente/notificacoes/ler'||url.pathname.startsWith('/cliente/push/')||url.pathname==='/suporte'||url.pathname.startsWith('/suporte/')))url.pathname=prefix+url.pathname;
  return url.href;
 }
 const fetch0=window.fetch;
 window.fetch=function(input,options){
  if(input instanceof Request){const url=scoped(input.url);return fetch0.call(this,url===input.url?input:new Request(url,input),options);}
  return fetch0.call(this,scoped(input),options);
 };
 document.addEventListener('click',event=>{const link=event.target.closest?.('a[href]');if(link)link.href=scoped(link.href);},true);
 document.addEventListener('submit',event=>{if(event.target.action)event.target.action=scoped(event.target.action);},true);
})();
