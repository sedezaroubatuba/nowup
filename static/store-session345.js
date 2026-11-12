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
 function navigation(value){
  const url=new URL(scoped(value),location.href);
  if(url.origin!==location.origin)return url.href;
  // Explicit merchant entry uses the existing role-checked login and panel.
  // Customer login, recovery and orders must keep their store-specific session.
  if(url.pathname==='/entrar'&&url.searchParams.get('tipo')==='profissional')return new URL('/entrar?tipo=profissional',location.origin).href;
  if(url.pathname==='/painel')return new URL('/painel',location.origin).href;
  const routes={'/entrar':store.login,'/cadastro/cliente':store.signup,'/recuperar-senha':store.forgot,'/cliente':store.orders,'/sair':store.logout};
  if(routes[url.pathname])return new URL(routes[url.pathname],location.origin).href;
  if(url.pathname===prefix||url.pathname===prefix+'/menu')return new URL(store.menu,location.origin).href;
  if(url.pathname.startsWith(prefix+'/')||url.pathname.startsWith('/static/')||url.pathname.startsWith('/uploads/'))return url.href;
  return new URL(store.menu,location.origin).href;
 }
 let checking420=false,lastCheck420=0;
 async function resume420(){if(document.hidden||checking420||node.dataset.demoBrowse386==='1'||Date.now()-lastCheck420<1500)return;checking420=true;lastCheck420=Date.now();try{const response=await fetch0.call(window,prefix+'/sessao420',{credentials:'same-origin',cache:'no-store'});if(!response.ok)return;const data=await response.json();if(typeof data.authenticated!=='boolean')return;const wasAuthenticated=node.dataset.loginRequired==='0',nowAuthenticated=data.authenticated&&data.role==='customer',renderedId=Number(node.dataset.customerId420||0);if(wasAuthenticated!==nowAuthenticated||(nowAuthenticated&&renderedId&&renderedId!==Number(data.user_id))){location.reload();}}catch(_){}finally{checking420=false;}}
 window.addEventListener('pageshow',resume420);window.addEventListener('focus',resume420);window.addEventListener('online',resume420);document.addEventListener('visibilitychange',()=>{if(!document.hidden)resume420();});
 document.addEventListener('click',event=>{const link=event.target.closest?.('a[href]');if(link)link.href=navigation(link.href);},true);
 document.addEventListener('submit',event=>{if(event.target.action)event.target.action=scoped(event.target.action);},true);
})();
