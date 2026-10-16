/* Display the CURRENT order state alongside historical notification text. */
(() => {
 const list=document.querySelector('[data-notification-list]');if(!list)return;
 let states={},busy=false;
 function render(){
  list.querySelectorAll('[data-notification-id]').forEach(row=>{
   const state=states[row.dataset.notificationId];if(!state)return;
   let badge=row.querySelector('[data-notification-status200]');
   if(!badge){badge=document.createElement('span');badge.dataset.notificationStatus200='';badge.setAttribute('role','status');row.querySelector('a')?.before(badge);}
   const text=state.order_code+' · '+state.label;
   if(badge.textContent!==text)badge.textContent=text;
   const cls='nu200-order-status status-'+state.status;if(badge.className!==cls)badge.className=cls;
  });
 }
 async function update(){
  if(busy||document.hidden)return;busy=true;
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),10000);
  try{const response=await fetch('/painel/notificacoes/status200',{credentials:'same-origin',cache:'no-store',signal:controller.signal});if(response.ok){states=(await response.json()).orders||{};render();}}catch(_){}finally{clearTimeout(timer);busy=false;}
 }
 new MutationObserver(render).observe(list,{childList:true,subtree:true});
 document.addEventListener('visibilitychange',()=>{if(!document.hidden)update();});
 update();setInterval(update,10000);
})();
