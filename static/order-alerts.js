(() => {
  'use strict';
  const root=document.querySelector('[data-order-alerts]');if(!root||window.__nowupOrderAlerts149)return;window.__nowupOrderAlerts149=true;
  const button=root.querySelector('[data-enable-order-alerts]'),status=root.querySelector('[data-alert-status]');
  const box=document.querySelector('[data-new-order-alert]'),message=document.querySelector('[data-new-order-message]'),open=document.querySelector('[data-open-new-order]');
  let cursor=Number(root.dataset.latestOrderId||0),audio,enabled=false,busy=false,lastAlarm=0,pendingId=0;
  const title=document.title;const testButton=root.querySelector('[data-test-order-alerts]'),disableButton=root.querySelector('[data-disable-order-alerts]');
  function running(){return enabled&&audio?.state==='running';}
  const stored=()=>{try{return localStorage.getItem('nowup-order-alerts')!=='0';}catch(_){return false;}};
  function render(){const on=running();root.dataset.soundState=on?'active':'inactive';button.textContent=on?'✓ Campainha ativada':'🔊 ATIVAR CAMPAINHA';button.disabled=on;testButton.hidden=!on;disableButton.hidden=!enabled;status.textContent=on?'Campainha pronta. Novos pedidos tocam até serem atendidos.':'Som não está liberado. Toque em ATIVAR CAMPAINHA e confirme que ouviu o teste.';}
  async function unlock(){try{if(!audio||audio.state==='closed'){audio=new(window.AudioContext||window.webkitAudioContext)();audio.onstatechange=()=>{render();if(running()&&pendingId){alarm();lastAlarm=Date.now();}};}await audio.resume();return audio.state==='running';}catch(_){return false;}}
  let tones=[];
  function silence(){tones.forEach(o=>{try{o.stop();}catch(_){}});tones=[];}
  function alarm(){if(!enabled||audio?.state!=='running')return;silence();try{const start=audio.currentTime;for(let i=0;i<5;i++){[1046,784].forEach((f,j)=>{const o=audio.createOscillator(),g=audio.createGain(),t=start+i*.4+j*.18;o.type='square';o.frequency.value=f;g.gain.setValueAtTime(.0001,t);g.gain.exponentialRampToValueAtTime(.6,t+.01);g.gain.exponentialRampToValueAtTime(.0001,t+.16);o.connect(g).connect(audio.destination);o.start(t);o.stop(t+.18);tones.push(o);});}navigator.vibrate?.([250,100,250,100,400]);}catch(_){}}
  button.addEventListener('click',async()=>{enabled=await unlock();try{localStorage.setItem('nowup-order-alerts',enabled?'1':'0');}catch(_){}render();if(enabled){alarm();lastAlarm=Date.now();}check();});
  testButton.addEventListener('click',async()=>{enabled=await unlock();render();if(running()){alarm();lastAlarm=Date.now();}check();});
  disableButton.addEventListener('click',()=>{enabled=false;silence();try{localStorage.setItem('nowup-order-alerts','0');}catch(_){}render();});
  async function restore(event){if(event?.target?.closest('[data-enable-order-alerts],[data-test-order-alerts],[data-disable-order-alerts]'))return;if(!running()&&stored()){enabled=await unlock();render();if(enabled&&pendingId){alarm();lastAlarm=Date.now();}}}
  document.addEventListener('pointerdown',restore);document.addEventListener('keydown',restore);
  open?.addEventListener('click',()=>{if(pendingId)location.assign('/painel?abrir_pedido='+pendingId+'#pedido-'+pendingId);});
  async function check(){
    if(busy)return;busy=true;const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),10000);
    try{
      const response=await fetch('/painel/pedidos/novos?after='+cursor,{credentials:'same-origin',cache:'no-store',signal:controller.signal});
      if(response.status===401||response.status===403){enabled=false;pendingId=0;silence();box.hidden=true;document.title=title;status.textContent='Entre na conta para continuar recebendo avisos.';return;}
      if(!response.ok)throw new Error();const data=await response.json();cursor=Math.max(cursor,Number(data.latest_id||0));
      if(data.pending_count>0&&data.pending_order){
        pendingId=data.pending_order.id;message.textContent=`${data.pending_count} pedido(s) aguardando aceite. ${data.pending_order.customer_name||'Cliente'} — R$ ${(data.pending_order.total_cents/100).toFixed(2).replace('.',',')}`;box.hidden=false;document.title='🔔 Pedido aguardando | NowUp';
        if(enabled&&Date.now()-lastAlarm>=2200){alarm();lastAlarm=Date.now();}
      }else{silence();pendingId=0;box.hidden=true;document.title=title;lastAlarm=0;}
      render();if(pendingId&&!running())status.textContent='PEDIDO AGUARDANDO! Toque em ATIVAR CAMPAINHA para liberar o som.';
    }catch(_){status.textContent='Conexão instável. Tentando novamente sem fechar o painel.';}
    finally{clearTimeout(timer);busy=false;}
  }
  render();restore();check();setInterval(check,2000);setInterval(()=>{if(pendingId&&enabled&&Date.now()-lastAlarm>=2200){alarm();lastAlarm=Date.now();}},200);window.addEventListener('online',check);document.addEventListener('visibilitychange',()=>{if(!document.hidden){render();check();}});
})();
