(() => {
 const box=document.querySelector('[data-push75]'); if(!box)return;
 const message=box.querySelector('[data-push-message]');
 const activate=box.querySelector('[data-push-enable]'), disable=box.querySelector('[data-push-disable]'), test=box.querySelector('[data-push-test]');
 const supported=window.isSecureContext && 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
 let busy=false;
 async function api(path, body) {
  const response=await fetch('/painel/push/'+path,{method:path==='config'?'GET':'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});
  if(!response.ok){let data={};try{data=await response.json()}catch(_){}throw new Error(data.detail || 'Não foi possível salvar. Entre na conta novamente e tente outra vez.');}
  return response.json();
 }
 function state(on){activate.hidden=on;disable.hidden=!on;test.hidden=!on;}
 function key(value){const raw=atob(value.replace(/-/g,'+').replace(/_/g,'/')+'='.repeat((4-value.length%4)%4));return Uint8Array.from(raw,c=>c.charCodeAt(0));}
 async function action(fn){if(busy)return;busy=true;try{await fn()}catch(e){message.textContent=e.message}finally{busy=false}}
 activate.onclick=()=>action(async()=>{
  if(!supported)return;
  const permission=await Notification.requestPermission();
  if(permission!=='granted')throw new Error('Permita notificações nas configurações do navegador para receber avisos.');
  const config=await api('config');
  await navigator.serviceWorker.register('/nowup-push-sw.js',{scope:'/'});
  const registration=await navigator.serviceWorker.ready;
  let subscription=await registration.pushManager.getSubscription();
  if(!subscription)subscription=await registration.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:key(config.publicKey)});
  await api('ativar',subscription.toJSON());state(true);message.textContent='Avisos ativados neste aparelho. Use Testar aviso para conferir.';
 });
 disable.onclick=()=>action(async()=>{
  await api('desativar');const registration=await navigator.serviceWorker.getRegistration('/');
  const subscription=await registration?.pushManager.getSubscription();if(subscription)await subscription.unsubscribe();
  state(false);message.textContent='Avisos desativados neste aparelho.';
 });
 test.onclick=()=>action(async()=>{await api('testar');message.textContent='Teste enviado. Confira a notificação do aparelho.'});
 state(false);
 if(!supported){activate.disabled=true;message.textContent='Este navegador não oferece avisos aqui. No iPhone, adicione o NowUp à Tela de Início e abra por esse ícone.';return;}
 action(async()=>{const registration=await navigator.serviceWorker.getRegistration('/');const subscription=await registration?.pushManager.getSubscription();if(subscription&&Notification.permission==='granted'){await api('ativar',subscription.toJSON());state(true);message.textContent='Avisos ativados neste aparelho.'}});
})();
