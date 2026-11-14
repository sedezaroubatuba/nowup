(()=>{'use strict';
 const root=document.querySelector('[data-order-link377]');if(!root)return;
 const waiting=new Set(['new','awaiting_payment','reviewing','awaiting_approval','revision_approved']),payable=new Set(['awaiting_payment','confirmed','preparing','ready','out_for_delivery','completed']),closed=new Set(['completed','cancelled','rejected','whatsapp_finalized']);
 function select(id){root.querySelectorAll('[role=tab]').forEach(b=>{const active=b.getAttribute('aria-controls')===id;b.setAttribute('aria-selected',String(active));document.getElementById(b.getAttribute('aria-controls')).hidden=!active;});history.replaceState(null,'','#'+id);}
 root.querySelectorAll('[role=tab]').forEach(b=>b.addEventListener('click',()=>select(b.getAttribute('aria-controls'))));
 if(['#pedido377','#conversa377','#pagamento377'].includes(location.hash))select(location.hash.slice(1));
 else if(root.dataset.customer390==='1'&&root.dataset.payment390==='pix'&&payable.has(root.dataset.currentStatus))select('pagamento377');
 root.querySelector('[data-open-conversa377]')?.addEventListener('click',()=>select('conversa377'));
 root.querySelector('[data-copy-order377]')?.addEventListener('click',async()=>{const box=root.querySelector('[data-copy-feedback377]');try{await navigator.clipboard.writeText(location.origin+root.dataset.shareUrl377);box.textContent='Link copiado. Envie ao cliente para conferir o pedido e o pagamento.';}catch(_){box.textContent='Copie o endereço desta página e envie ao cliente.';}});
 function paymentConfirmed419(){const payment=document.getElementById('pagamento377');if(payment&&!payment.querySelector('[data-pix-confirmed405]')){const notice=document.createElement('p');notice.dataset.pixConfirmed405='';notice.setAttribute('role','status');notice.style.cssText='background:#dcfce7;color:#166534;padding:20px;border-radius:14px;font-weight:700';notice.textContent='✅ Seu pagamento foi aprovado. Aguarde os próximos status do pedido.';payment.replaceChildren(notice);}}
 function contact432(){
  if(['new','whatsapp_finalized'].includes(root.dataset.currentStatus)){root.querySelector('[data-contact432]')?.remove();return;}
  const customer=root.dataset.customer390==='1';let phone=(customer?root.dataset.storeWhatsapp432:root.dataset.buyerWhatsapp432)||'';phone=phone.replace(/\D/g,'');if(phone.length===10||phone.length===11)phone='55'+phone;if(!/^55\d{10,11}$/.test(phone))return;
  let box=root.querySelector('[data-contact432]');if(!box){box=document.createElement('section');box.dataset.contact432='';box.style.cssText='padding:16px;margin:16px 0;border:1px solid #b7dfc4;border-radius:14px';root.append(box);}
  const labels={new:'aguardando revisão da loja',confirmed:'confirmado',preparing:'em preparo',ready:'pronto',out_for_delivery:'a caminho',completed:'concluído',cancelled:'cancelado',rejected:'recusado'};
  const message=customer?'Olá! Gostaria de falar sobre meu pedido '+root.dataset.orderCode432+'.':'Olá! Seu pedido '+root.dataset.orderCode432+' está '+(labels[root.dataset.currentStatus]||'em atualização')+'. Confira o acompanhamento no NowUp.';
  box.replaceChildren();const a=document.createElement('a');a.className='btn primary full-btn';a.style.background='#16883f';a.target='_blank';a.rel='noopener';a.href='https://wa.me/'+phone+'?text='+encodeURIComponent(message);a.textContent=customer?'Falar com a loja pelo WhatsApp':'Avisar cliente pelo WhatsApp';box.append(a);
 }
 contact432();
 function offerPixMessage430(){
  const payment=document.getElementById('pagamento377');if(!payment?.querySelector('[data-pix-confirmed405]')||payment.querySelector('[data-pix-whatsapp430]')||!root.hasAttribute('data-pix-customer430'))return;
  let phone=root.dataset.pixCustomer430.replace(/\D/g,'');if(phone.length===10||phone.length===11)phone='55'+phone;if(!/^55\d{10,11}$/.test(phone))return;
  const status=root.dataset.currentStatus;
  const preparing=['new','awaiting_payment','confirmed','preparing'].includes(status);
  let message='✅ Pix confirmado!';
  if(preparing)message+='\n\nSeu pedido já está em preparo. '+(root.dataset.fulfillment430==='pickup'?'Assim que estiver pronto para retirada, avisaremos por aqui. 🛍️💜':'Assim que sair para entrega, avisaremos por aqui. 🛵💜');
  else message+='\n\nRecebemos o pagamento do seu pedido. Obrigado! 💜';
  if(root.dataset.orderCode430)message+='\nPedido '+root.dataset.orderCode430;
  const link=document.createElement('a');link.dataset.pixWhatsapp430='';link.className='btn primary full-btn';link.target='_blank';link.rel='noopener';link.href='https://wa.me/'+phone+'?text='+encodeURIComponent(message);link.textContent='Avisar cliente: Pix confirmado';payment.append(link);
  const hint=document.createElement('p');hint.textContent='O pagamento foi registrado. Toque no botão e depois em Enviar no WhatsApp para avisar o cliente.';payment.append(hint);
 }
 offerPixMessage430();
 root.addEventListener('submit',async event=>{const form=event.target;if(!form.matches('[data-confirm-pix419]'))return;event.preventDefault();event.stopPropagation();if(form.dataset.saving419||!form.reportValidity())return;form.dataset.saving419='1';const button=form.querySelector('[type=submit]'),feedback=form.querySelector('[data-pix-feedback419]');button.disabled=true;feedback.textContent='Confirmando recebimento…';const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),15000);try{const response=await fetch(form.action,{method:'POST',credentials:'same-origin',cache:'no-store',headers:{Accept:'application/json'},body:new FormData(form),signal:controller.signal});let data;try{data=await response.json();}catch(_){}if(!response.ok||data?.payment_confirmed!==true||String(data.id)!==form.dataset.orderId419)throw Error(typeof data?.detail==='string'?data.detail:'Não foi possível confirmar. Confira o pedido e tente novamente.');paymentConfirmed419();offerPixMessage430();window.dispatchEvent(new Event('focus'));}catch(error){feedback.textContent=error.name==='AbortError'?'A resposta demorou. Confira o pagamento antes de tentar novamente.':error.message;}finally{clearTimeout(timeout);delete form.dataset.saving419;button.disabled=false;}},true);
 // Keep the clicked submitter enabled so its status=confirmed value is posted.
 let current=root.dataset.currentStatus,busy=false,timer=null,stopped=false;
 const interval=()=>2000;
 function schedule(){clearTimeout(timer);if(!stopped)timer=setTimeout(poll,interval());}
 async function poll(){clearTimeout(timer);if(stopped)return;if(document.hidden||busy){schedule();return;}busy=true;const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),6000);
  try{const r=await fetch(root.dataset.statusUrl,{credentials:'same-origin',cache:'no-store',signal:controller.signal});if(r.status===401||r.status===403||r.status===404){stopped=true;return;}if(!r.ok)return;const data=await r.json();const changed=data.status!==current||Boolean(root.dataset.updated377&&data.updated_at!==root.dataset.updated377);
   if(data.payment_confirmed&&payable.has(data.status)){paymentConfirmed419();offerPixMessage430();}
   if(changed){
    if(root.dataset.customer390==='1'&&root.dataset.payment390==='pix'&&waiting.has(current)&&payable.has(data.status))select('pagamento377');
    const response=await fetch(location.pathname,{credentials:'same-origin',cache:'no-store',signal:controller.signal});
    if(!response.ok)return;
    const doc=new DOMParser().parseFromString(await response.text(),'text/html');
    for(const id of ['orderHero434','pedido377','pagamento377']){const old=document.getElementById(id),fresh=doc.getElementById(id);if(old&&fresh){old.replaceChildren(...fresh.childNodes);}}
    root.querySelectorAll('[data-pix-payment]').forEach(host=>{const config=host.querySelector('script[type="application/json"]');if(config&&window.NOWUP_PIX){window.NOWUP_PIX.attach(host,JSON.parse(config.textContent));}});
    current=data.status;root.dataset.currentStatus=current;root.dataset.updated377=data.updated_at;offerPixMessage430();contact432();return;
   }root.dataset.updated377=data.updated_at;
  }catch(_){}finally{clearTimeout(timeout);busy=false;schedule();}
 }
 window.addEventListener('online',poll);window.addEventListener('focus',poll);window.addEventListener('pageshow',poll);document.addEventListener('visibilitychange',()=>{if(!document.hidden)poll();});poll();
})();
