(()=>{
  const root=document.querySelector('[data-order-alerts]');if(!root)return;
  const button=root.querySelector('[data-enable-order-alerts]'),status=root.querySelector('[data-alert-status]'),alertBox=document.querySelector('[data-new-order-alert]'),message=document.querySelector('[data-new-order-message]'),openButton=document.querySelector('[data-open-new-order]');
  let latest=Number(root.dataset.latestOrderId||0),audioContext=null,enabled=false,checking=false,lastAlarm=0;
  const originalTitle=document.title;
  function render(){button.classList.toggle('active',enabled);button.textContent=enabled?'🔔 Alertas ativados':'🔔 Ativar alertas de pedidos';status.textContent=enabled?'O alarme continuará tocando enquanto houver pedido aguardando aceite.':'Toque aqui uma vez para liberar o som de novos pedidos.'}
  async function unlock(){try{audioContext=audioContext||new(window.AudioContext||window.webkitAudioContext)();await audioContext.resume();return audioContext.state==='running'}catch(_){return false}}
  function playAlarm(){
    if(!enabled||!audioContext||audioContext.state!=='running')return;
    const start=audioContext.currentTime,notes=[880,1174,1396,1174,1760];
    notes.forEach((frequency,index)=>{const oscillator=audioContext.createOscillator(),gain=audioContext.createGain();oscillator.type='square';oscillator.frequency.value=frequency;gain.gain.setValueAtTime(.0001,start+index*.28);gain.gain.exponentialRampToValueAtTime(.5,start+index*.28+.02);gain.gain.exponentialRampToValueAtTime(.0001,start+index*.28+.22);oscillator.connect(gain).connect(audioContext.destination);oscillator.start(start+index*.28);oscillator.stop(start+index*.28+.24)});
    if(navigator.vibrate)navigator.vibrate([350,150,350,150,350,150,350,150,600]);
  }
  button.addEventListener('click',async()=>{enabled=!enabled;if(enabled){const ok=await unlock();if(!ok)enabled=false}localStorage.setItem('nowup-order-alerts',enabled?'1':'0');render();if(enabled)playAlarm();if(enabled&&'Notification'in window&&Notification.permission==='default')Notification.requestPermission()});
  const restore=async()=>{if(localStorage.getItem('nowup-order-alerts')==='1'&&!enabled){enabled=await unlock();render()}document.removeEventListener('pointerdown',restore);document.removeEventListener('keydown',restore)};document.addEventListener('pointerdown',restore,{once:true});document.addEventListener('keydown',restore,{once:true});
  openButton?.addEventListener('click',()=>{location.href='/painel#pedidos'});
  function showPending(order,count){if(!order)return;message.textContent=`${count} pedido${count>1?'s':''} aguardando aceite. Mais recente: #${order.id}, ${order.customer_name} — R$ ${(order.total_cents/100).toFixed(2).replace('.',',')}`;alertBox.hidden=false;document.title=`🔔 ${count} PEDIDO${count>1?'S':''} AGUARDANDO | NowUp`}
  async function check(){if(checking)return;checking=true;try{const response=await fetch(`/painel/pedidos/novos?after=${latest}`,{cache:'no-store'});if(!response.ok)return;const data=await response.json();latest=Math.max(latest,Number(data.latest_id||0));const pending=Number(data.pending_count||0);if(pending>0&&data.pending_order){showPending(data.pending_order,pending);const now=Date.now();if(now-lastAlarm>=10000){playAlarm();lastAlarm=now}if(enabled&&data.orders?.length&&'Notification'in window&&Notification.permission==='granted')new Notification('Novo pedido no NowUp',{body:`${data.pending_order.customer_name} — aguardando aceite`})}else{alertBox.hidden=true;document.title=originalTitle;lastAlarm=0}}catch(_){}finally{checking=false}}
  const ordersPanel=document.querySelector('#pedidos'),activeCards=document.querySelectorAll('[data-order-status="new"],[data-order-status="confirmed"],[data-order-status="preparing"],[data-order-status="ready"],[data-order-status="out_for_delivery"]');if(ordersPanel&&activeCards.length){ordersPanel.classList.add('has-active-orders');alertBox.insertAdjacentElement('afterend',ordersPanel)}
  render();check();setInterval(check,3000);document.addEventListener('visibilitychange',()=>{if(!document.hidden)check()});
})();
