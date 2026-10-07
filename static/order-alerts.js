(()=>{
  const root=document.querySelector('[data-order-alerts]');
  if(!root)return;

  const button=root.querySelector('[data-enable-order-alerts]');
  const status=root.querySelector('[data-alert-status]');
  const alertBox=document.querySelector('[data-new-order-alert]');
  const message=document.querySelector('[data-new-order-message]');
  const openButton=document.querySelector('[data-open-new-order]');
  const badge=document.querySelector('[data-notification-badge]');
  const notificationList=document.querySelector('[data-notification-list]');

  let latest=Number(root.dataset.latestOrderId||0);
  let latestNotification=Number(root.dataset.latestNotificationId||0);
  let audioContext=null;
  let enabled=false;
  let checking=false;
  let lastAlarm=0;
  const originalTitle=document.title;

  function render(){
    if(!button||!status)return;
    button.classList.toggle('active',enabled);
    button.textContent=enabled?'🔔 Alertas ativados':'🔔 Ativar alertas de pedidos';
    status.textContent=enabled
      ?'5 toques serão repetidos enquanto houver pedido novo aguardando aceite.'
      :'Toque aqui uma vez para liberar o som dos novos pedidos.';
  }

  async function unlock(){
    try{
      audioContext=audioContext||new(window.AudioContext||window.webkitAudioContext)();
      await audioContext.resume();
      return audioContext.state==='running';
    }catch(_){return false;}
  }

  function playAlarm(){
    if(!enabled||!audioContext||audioContext.state!=='running')return;
    const start=audioContext.currentTime;
    const notes=[880,1174,1396,1174,1760];
    notes.forEach((frequency,index)=>{
      const oscillator=audioContext.createOscillator();
      const gain=audioContext.createGain();
      oscillator.type='square';
      oscillator.frequency.value=frequency;
      gain.gain.setValueAtTime(.0001,start+index*.28);
      gain.gain.exponentialRampToValueAtTime(.45,start+index*.28+.02);
      gain.gain.exponentialRampToValueAtTime(.0001,start+index*.28+.22);
      oscillator.connect(gain).connect(audioContext.destination);
      oscillator.start(start+index*.28);
      oscillator.stop(start+index*.28+.24);
    });
    if(navigator.vibrate)navigator.vibrate([350,150,350,150,350,150,350,150,600]);
  }

  function updateBadge(count){
    if(!badge)return;
    badge.textContent=String(count);
    badge.hidden=count<=0;
  }

  function orderUrl(id){
    return `/painel?abrir_pedido=${encodeURIComponent(id)}&t=${Date.now()}#pedido-${encodeURIComponent(id)}`;
  }

  function showPending(order,count){
    if(!order||!alertBox||!message)return;
    const code=order.order_code||`#${order.id}`;
    message.textContent=`${count} pedido${count>1?'s':''} aguardando aceite. Mais recente: ${code}, ${order.customer_name||'Cliente'} — R$ ${(Number(order.total_cents||0)/100).toFixed(2).replace('.',',')}`;
    alertBox.hidden=false;
    if(openButton)openButton.dataset.pendingOrderId=String(order.id);
    document.title=`🔔 ${count} PEDIDO${count>1?'S':''} AGUARDANDO | NowUp`;
    updateBadge(count);
  }

  function hidePending(){
    if(alertBox)alertBox.hidden=true;
    document.title=originalTitle;
    lastAlarm=0;
    updateBadge(0);
  }

  function addNotification(item){
    if(!notificationList||!item||document.querySelector(`[data-notification-id="${item.id}"]`))return;
    notificationList.querySelector('[data-empty-notifications]')?.remove();
    const article=document.createElement('article');
    article.dataset.notificationId=String(item.id);
    const title=document.createElement('b');
    const body=document.createElement('p');
    const link=document.createElement('a');
    title.textContent=item.title||'Notificação';
    body.textContent=item.message||'';
    link.className='btn soft';
    link.href=item.link||'#pedidos';
    link.dataset.notificationLink='';
    link.textContent='Abrir pedido';
    article.append(title,body,link);
    notificationList.prepend(article);
  }

  async function checkNotifications(){
    try{
      const response=await fetch(`/painel/notificacoes/recentes?after=${latestNotification}`,{cache:'no-store'});
      if(!response.ok)return;
      const data=await response.json();
      (data.notifications||[]).forEach(addNotification);
      latestNotification=Math.max(latestNotification,Number(data.latest_id||0));
    }catch(_){/* o alerta de pedidos continua funcionando mesmo se esta consulta falhar */}
  }

  button?.addEventListener('click',async()=>{
    if(enabled){
      enabled=false;
      localStorage.setItem('nowup-order-alerts','0');
      render();
      return;
    }
    enabled=await unlock();
    localStorage.setItem('nowup-order-alerts',enabled?'1':'0');
    render();
    if(enabled){
      playAlarm();
      if('Notification'in window&&Notification.permission==='default'){
        try{await Notification.requestPermission();}catch(_){/* sem notificação nativa, mantém alerta interno */}
      }
    }
  });

  const restore=async event=>{
    if(localStorage.getItem('nowup-order-alerts')!=='1'||enabled)return;
    if(button&&event?.target===button)return;
    enabled=await unlock();
    render();
  };
  document.addEventListener('pointerdown',restore,{once:true});
  document.addEventListener('keydown',restore,{once:true});

  openButton?.addEventListener('click',()=>{
    const id=Number(openButton.dataset.pendingOrderId||0);
    location.assign(id?orderUrl(id):`/painel?t=${Date.now()}#pedidos`);
  });

  async function check(){
    if(checking)return;
    checking=true;
    try{
      const response=await fetch(`/painel/pedidos/novos?after=${latest}`,{cache:'no-store'});
      if(!response.ok){
        if(status)status.textContent=response.status===401||response.status===403
          ?'Sua sessão expirou. Entre novamente para receber pedidos.'
          :'Falha ao consultar pedidos. Tentando novamente…';
        return;
      }
      const data=await response.json();
      const incoming=(data.orders||[]);
      latest=Math.max(latest,Number(data.latest_id||0));
      const pending=Number(data.pending_count||0);

      if(pending>0&&data.pending_order){
        showPending(data.pending_order,pending);
        const now=Date.now();
        if(now-lastAlarm>=7000){playAlarm();lastAlarm=now;}
        if(enabled&&incoming.length&&'Notification'in window&&Notification.permission==='granted'){
          const newest=incoming[incoming.length-1];
          try{new Notification('Novo pedido no NowUp',{body:`${newest.customer_name||'Cliente'} — aguardando aceite`});}catch(_){/* alerta interno continua */}
        }
      }else{
        hidePending();
      }
      await checkNotifications();
    }catch(_){
      if(status)status.textContent='Sem conexão para consultar pedidos. Tentando novamente…';
    }finally{
      checking=false;
    }
  }

  render();
  check();
  setInterval(check,3000);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)check();});
})();
