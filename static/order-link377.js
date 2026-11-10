(()=>{'use strict';
 const root=document.querySelector('[data-order-link377]');if(!root)return;
 const waiting=new Set(['new','reviewing','awaiting_approval','revision_approved']),payable=new Set(['new','confirmed','preparing','ready','out_for_delivery','completed']),closed=new Set(['completed','cancelled','rejected','whatsapp_finalized']);
 function select(id){root.querySelectorAll('[role=tab]').forEach(b=>{const active=b.getAttribute('aria-controls')===id;b.setAttribute('aria-selected',String(active));document.getElementById(b.getAttribute('aria-controls')).hidden=!active;});history.replaceState(null,'','#'+id);}
 root.querySelectorAll('[role=tab]').forEach(b=>b.addEventListener('click',()=>select(b.getAttribute('aria-controls'))));
 if(['#pedido377','#conversa377','#pagamento377'].includes(location.hash))select(location.hash.slice(1));
 else if(root.dataset.customer390==='1'&&root.dataset.payment390==='pix'&&payable.has(root.dataset.currentStatus))select('pagamento377');
 root.querySelector('[data-open-conversa377]')?.addEventListener('click',()=>select('conversa377'));
 root.querySelector('[data-copy-order377]')?.addEventListener('click',async()=>{const box=root.querySelector('[data-copy-feedback377]');try{await navigator.clipboard.writeText(location.origin+root.dataset.shareUrl377);box.textContent='Link copiado. Envie ao cliente para conferir o pedido e o pagamento.';}catch(_){box.textContent='Copie o endereço desta página e envie ao cliente.';}});
 // Keep the clicked submitter enabled so its status=confirmed value is posted.
 root.querySelector('[data-confirm390]')?.form.addEventListener('submit',e=>{const form=e.currentTarget;if(form.dataset.sending390){e.preventDefault();return;}form.dataset.sending390='1';const b=form.querySelector('[data-confirm390]');b.textContent='Aceitando pedido…';b.setAttribute('aria-disabled','true');b.style.pointerEvents='none';});
 let current=root.dataset.currentStatus,busy=false,timer=null,stopped=closed.has(current);
 const interval=()=>waiting.has(current)?2000:8000;
 function schedule(){clearTimeout(timer);if(!stopped)timer=setTimeout(poll,interval());}
 async function poll(){clearTimeout(timer);if(stopped)return;if(document.hidden||busy){schedule();return;}busy=true;const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),6000);
  try{const r=await fetch(root.dataset.statusUrl,{credentials:'same-origin',cache:'no-store',signal:controller.signal});if(r.status===401||r.status===403||r.status===404){stopped=true;return;}if(!r.ok)return;const data=await r.json();const changed=data.status!==current||Boolean(root.dataset.updated377&&data.updated_at!==root.dataset.updated377);
   if(changed){
    if(root.dataset.customer390==='1'&&root.dataset.payment390==='pix'&&waiting.has(current)&&payable.has(data.status))history.replaceState(null,'','#pagamento377');
    location.reload();stopped=true;return;
   }root.dataset.updated377=data.updated_at;
  }catch(_){}finally{clearTimeout(timeout);busy=false;schedule();}
 }
 window.addEventListener('online',poll);window.addEventListener('focus',poll);window.addEventListener('pageshow',poll);document.addEventListener('visibilitychange',()=>{if(!document.hidden)poll();});poll();
})();
