(() => {
  'use strict';
  const root=document.querySelector('[data-customer-alerts112]');if(!root)return;
  const button=root.querySelector('[data-customer-enable]'),test=root.querySelector('[data-customer-test]'),disable=root.querySelector('[data-customer-disable]'),status=root.querySelector('[data-customer-alert-status]'),banner=root.querySelector('[data-customer-update]');
  let cursor=-1,busy=false,activating=false,audio,enabled=false;
  const labels={new:'Pedido recebido',confirmed:'Pedido aceito',preparing:'Em preparo',ready:'Pronto',out_for_delivery:'Saiu para entrega',completed:'Concluído',cancelled:'Cancelado',rejected:'Recusado'};
  function preference(){try{return localStorage.getItem('nowup-customer-sound')==='1';}catch(_){return false;}}
  async function unlock(){try{audio=audio||new(window.AudioContext||window.webkitAudioContext)();await audio.resume();return audio.state==='running';}catch(_){return false;}}
  function beep(){if(!enabled||audio?.state!=='running')return;try{[880,1174,1396].forEach((frequency,i)=>{const o=audio.createOscillator(),g=audio.createGain(),start=audio.currentTime+i*.3;o.frequency.value=frequency;g.gain.setValueAtTime(.0001,start);g.gain.exponentialRampToValueAtTime(.15,start+.02);g.gain.exponentialRampToValueAtTime(.0001,start+.2);o.connect(g).connect(audio.destination);o.start(start);o.stop(start+.22);});}catch(_){}}
  async function api(path,body){const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),12000);try{const r=await fetch('/cliente/push/'+path,{method:path==='config'?'GET':'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined,signal:controller.signal});const data=await r.json();if(!r.ok)throw new Error(data.detail||'Não foi possível ativar.');return data;}finally{clearTimeout(timer);}}
  const supported=window.isSecureContext&&'serviceWorker' in navigator&&'PushManager' in window&&'Notification' in window;
  const key=value=>{const raw=atob(value.replace(/-/g,'+').replace(/_/g,'/')+'='.repeat((4-value.length%4)%4));return Uint8Array.from(raw,c=>c.charCodeAt(0));};
  button.addEventListener('click',async()=>{
    if(activating)return;activating=true;button.disabled=true;
    const permission=supported?Notification.requestPermission():Promise.resolve('unsupported');
    try{
      enabled=await unlock();try{localStorage.setItem('nowup-customer-sound',enabled?'1':'0');}catch(_){}
      if(await permission!=='granted'){status.textContent='Som ativado enquanto a página estiver aberta. Para avisos com ela fechada, permita notificações em um navegador compatível.';return;}
      const config=await api('config');const registration=await navigator.serviceWorker.register('/nowup-push-sw.js',{scope:'/'});
      let sub=await registration.pushManager.getSubscription();
      if(!sub){await new Promise((resolve,reject)=>{if(registration.active)return resolve();const worker=registration.installing||registration.waiting;if(!worker)return reject(new Error('Atualize a página e tente novamente.'));const timer=setTimeout(()=>reject(new Error('Atualize a página e tente novamente.')),12000);worker.addEventListener('statechange',()=>{if(worker.state==='activated'){clearTimeout(timer);resolve();}});});sub=await registration.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:key(config.publicKey)});}
      await api('ativar',sub.toJSON());test.hidden=false;disable.hidden=false;status.textContent='Avisos ativados neste aparelho.';beep();
    }catch(e){status.textContent=e.message||'Não foi possível ativar. Tente novamente.';}finally{button.disabled=false;activating=false;}
  });
  test.addEventListener('click',async()=>{test.disabled=true;try{await api('testar');status.textContent='Teste enviado. Confira o aviso no celular.';}catch(e){status.textContent=e.message;}finally{test.disabled=false;}});
  disable.addEventListener('click',async()=>{disable.disabled=true;try{await api('desativar');enabled=false;try{localStorage.removeItem('nowup-customer-sound');}catch(_){}test.hidden=true;disable.hidden=true;status.textContent='Avisos desativados nesta conta.';}catch(e){status.textContent=e.message;}finally{disable.disabled=false;}});
  async function restore(){if(!enabled&&preference())enabled=await unlock();}
  document.addEventListener('pointerdown',restore);document.addEventListener('keydown',restore);
  async function check(){
    if(busy)return;busy=true;const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),10000);
    try{
      const r=await fetch('/cliente/avisos?after='+cursor,{credentials:'same-origin',cache:'no-store',signal:controller.signal});if(!r.ok)return;
      const data=await r.json();cursor=Number(data.cursor);
      for(const o of data.orders||[]){document.querySelectorAll(`[data-customer-order="${o.id}"]`).forEach(card=>{const target=card.querySelector('[data-customer-order-status]');if(target)target.textContent=labels[o.status]||o.status;});}
      const notes=data.notifications||[];
      if(notes.length){const last=notes[notes.length-1];banner.hidden=false;banner.textContent=last.title+': '+last.message;const url=new URL(last.link||'/cliente',location.origin);banner.href=url.origin===location.origin?url.href:'/cliente';beep();}
    }catch(_){}finally{clearTimeout(timer);busy=false;}
  }
  check();setInterval(check,5000);window.addEventListener('online',check);document.addEventListener('visibilitychange',()=>{if(!document.hidden)check();});
})();
