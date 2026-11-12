(()=>{'use strict';
 const root=document.querySelector('[data-order-link377]');if(!root)return;
 const waiting=new Set(['new','reviewing','awaiting_approval','revision_approved']),payable=new Set(['confirmed','preparing','ready','out_for_delivery','completed']),closed=new Set(['completed','cancelled','rejected','whatsapp_finalized']);
 function select(id){root.querySelectorAll('[role=tab]').forEach(b=>{const active=b.getAttribute('aria-controls')===id;b.setAttribute('aria-selected',String(active));document.getElementById(b.getAttribute('aria-controls')).hidden=!active;});history.replaceState(null,'','#'+id);}
 root.querySelectorAll('[role=tab]').forEach(b=>b.addEventListener('click',()=>select(b.getAttribute('aria-controls'))));
 if(['#pedido377','#conversa377','#pagamento377'].includes(location.hash))select(location.hash.slice(1));
 else if(root.dataset.customer390==='1'&&root.dataset.payment390==='pix'&&payable.has(root.dataset.currentStatus))select('pagamento377');
 root.querySelector('[data-open-conversa377]')?.addEventListener('click',()=>select('conversa377'));
 root.querySelector('[data-copy-order377]')?.addEventListener('click',async()=>{const box=root.querySelector('[data-copy-feedback377]');try{await navigator.clipboard.writeText(location.origin+root.dataset.shareUrl377);box.textContent='Link copiado. Envie ao cliente para conferir o pedido e o pagamento.';}catch(_){box.textContent='Copie o endereço desta página e envie ao cliente.';}});
 function paymentConfirmed419(){const payment=document.getElementById('pagamento377');if(payment&&!payment.querySelector('[data-pix-confirmed405]')){const notice=document.createElement('p');notice.dataset.pixConfirmed405='';notice.setAttribute('role','status');notice.style.cssText='background:#dcfce7;color:#166534;padding:20px;border-radius:14px;font-weight:700';notice.textContent='✓ Pix confirmado — recebimento conferido pela loja.';payment.replaceChildren(notice);}}
 root.addEventListener('submit',async event=>{const form=event.target;if(!form.matches('[data-confirm-pix419]'))return;event.preventDefault();event.stopPropagation();if(form.dataset.saving419||!form.reportValidity())return;form.dataset.saving419='1';const button=form.querySelector('[type=submit]'),feedback=form.querySelector('[data-pix-feedback419]');button.disabled=true;feedback.textContent='Confirmando recebimento…';const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),15000);try{const response=await fetch(form.action,{method:'POST',credentials:'same-origin',cache:'no-store',headers:{Accept:'application/json'},body:new FormData(form),signal:controller.signal});let data;try{data=await response.json();}catch(_){}if(!response.ok||data?.payment_confirmed!==true||String(data.id)!==form.dataset.orderId419)throw Error(typeof data?.detail==='string'?data.detail:'Não foi possível confirmar. Confira o pedido e tente novamente.');paymentConfirmed419();window.dispatchEvent(new Event('focus'));}catch(error){feedback.textContent=error.name==='AbortError'?'A resposta demorou. Confira o pagamento antes de tentar novamente.':error.message;}finally{clearTimeout(timeout);delete form.dataset.saving419;button.disabled=false;}},true);
 // Keep the clicked submitter enabled so its status=confirmed value is posted.
 let current=root.dataset.currentStatus,busy=false,timer=null,stopped=false;
 const interval=()=>2000;
 function schedule(){clearTimeout(timer);if(!stopped)timer=setTimeout(poll,interval());}
 async function poll(){clearTimeout(timer);if(stopped)return;if(document.hidden||busy){schedule();return;}busy=true;const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),6000);
  try{const r=await fetch(root.dataset.statusUrl,{credentials:'same-origin',cache:'no-store',signal:controller.signal});if(r.status===401||r.status===403||r.status===404){stopped=true;return;}if(!r.ok)return;const data=await r.json();const changed=data.status!==current||Boolean(root.dataset.updated377&&data.updated_at!==root.dataset.updated377);
   if(data.payment_confirmed&&payable.has(data.status))paymentConfirmed419();
   if(changed){
    if(root.dataset.customer390==='1'&&root.dataset.payment390==='pix'&&waiting.has(current)&&payable.has(data.status))select('pagamento377');
    const response=await fetch(location.pathname,{credentials:'same-origin',cache:'no-store',signal:controller.signal});
    if(!response.ok)return;
    const doc=new DOMParser().parseFromString(await response.text(),'text/html');
    for(const id of ['orderLiveStatus','pedido377','pagamento377']){const old=document.getElementById(id),fresh=doc.getElementById(id);if(old&&fresh){old.replaceChildren(...fresh.childNodes);}}
    root.querySelectorAll('[data-pix-payment]').forEach(host=>{const config=host.querySelector('script[type="application/json"]');if(config&&window.NOWUP_PIX){window.NOWUP_PIX.attach(host,JSON.parse(config.textContent));}});
    current=data.status;root.dataset.currentStatus=current;root.dataset.updated377=data.updated_at;return;
   }root.dataset.updated377=data.updated_at;
  }catch(_){}finally{clearTimeout(timeout);busy=false;schedule();}
 }
 window.addEventListener('online',poll);window.addEventListener('focus',poll);window.addEventListener('pageshow',poll);document.addEventListener('visibilitychange',()=>{if(!document.hidden)poll();});poll();
})();
