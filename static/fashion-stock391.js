/* Fashion only. Optimistic cart edits become usable only after a server hold. */
(()=>{'use strict';
 if(!document.body.classList.contains('fashion-catalog385'))return;
 const cfg=window.NOWUP_MENU||{},root=document.querySelector('[data-native-menu]');
 if(!root||cfg.demoBrowse386||!cfg.customerId||cfg.ownerView)return;
 const path=location.pathname.replace(/\/menu\/?$/,'').replace(/\/$/,'');
 const storageKey='fashion-basket391:'+cfg.customerId+':'+path;
 let basket;try{basket=localStorage.getItem(storageKey)||crypto.randomUUID();localStorage.setItem(storageKey,basket);}catch(_){basket=crypto.randomUUID();}
 const forms=[...root.querySelectorAll('form')].filter(f=>f.querySelector('[name=cart_json]'));
 forms.forEach(f=>{const i=document.createElement('input');i.type='hidden';i.name='basket_key391';i.value=basket;f.append(i);});
 const status=document.createElement('div');status.className='nu391-reservation';status.setAttribute('role','status');
 const label=document.createElement('span'),retry=document.createElement('button');retry.type='button';retry.textContent='Atualizar reserva';retry.hidden=true;status.append(label,retry);root.querySelector('.nu-menu-sticky')?.append(status);
 let accepted=[],last='',version=0,queue=Promise.resolve(),suppress=false,pending=false,valid=false,expires=0;
 const entries=()=>window.NOWUP_CART160?.entries389()||[];
 const payload=rows=>rows.map(v=>({id:v.productId,quantity:v.quantity,options:(v.options||[]).map(o=>({id:Number(o.id),quantity:o.quantity||1})),notes:v.notes||'',utensils:!!v.utensils,customization:v.customization||{groups:{},removed:[]}}));
 function buttons(){if(pending||!valid)root.querySelectorAll('[data-checkout],[data-dock-checkout],form [type=submit]').forEach(b=>b.disabled=true);}
 function stock(data){for(const product of data||[]){const card=root.querySelector('[data-product][data-id="'+product.id+'"]');if(!card||product.mode==='none')continue;card.dataset.liveStock391=JSON.stringify(product);const colors=[...card.querySelectorAll('[data-group192="fashionColor385"]')],sizes=[...card.querySelectorAll('[data-group192="fashionSize385"]')];const size=sizes.find(i=>i.checked)?.value||'',color=colors.find(i=>i.checked)?.value||'';
 const balance=(s,c)=>product.variants.filter(v=>(product.mode==='total'||!s||v.size===s)&&(product.mode!=='variants'||!c||v.color===c)).reduce((n,v)=>n+v.available,0);
 sizes.forEach(i=>{i.disabled=balance(i.value,color)<=0;i.closest('label').title=i.disabled?'Esgotado':'';});colors.forEach(i=>{i.disabled=product.mode==='variants'&&balance(size,i.value)<=0;i.closest('label').title=i.disabled?'Esgotado':'';});
 const left=balance(size,color),note=card.querySelector('.nu389-balance');if(note)note.textContent=left?left+' unidades disponíveis':'Esgotado';
 const add=card.querySelector('[data-add]');if(add){add.disabled=left===0;if(!left)add.textContent='Esgotado';else if(add.textContent==='Esgotado')add.textContent='Adicionar ao carrinho';}
 root.querySelectorAll('[data-source256="'+product.id+'"]').forEach(node=>{const toggle=node.querySelector('.nu201-open');if(toggle){toggle.disabled=product.variants.every(v=>v.available===0);toggle.dataset.stockSoldOut391=toggle.disabled?'1':'0';if(toggle.disabled)toggle.textContent='Esgotado';}});
 }}
 async function refresh(){try{const r=await fetch(path+'/menu/estoque?basket_key='+encodeURIComponent(basket),{cache:'no-store'});if(r.ok)stock((await r.json()).stock);}catch(_){} }
 function schedule(force=false){if(suppress)return;const rows=entries(),body=JSON.stringify(payload(rows));if(body===last&&!force){buttons();return;}last=body;const current=++version;pending=true;valid=false;label.textContent='Reservando peças…';retry.hidden=true;buttons();
 queue=queue.then(async()=>{try{const r=await fetch(path+'/menu/estoque/reservar',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({cart_json:body,basket_key:basket})});const d=await r.json();if(!r.ok)throw new Error(d.detail||'Não foi possível reservar as peças.');if(current!==version)return;accepted=rows;expires=d.expires_at*1000;valid=true;pending=false;label.textContent=rows.length?'Peças reservadas por até 10 minutos.':'';stock(d.stock);suppress=true;window.NOWUP_CART160.restore391(rows);suppress=false;
 }catch(e){if(current!==version)return;pending=false;valid=false;label.textContent=e.message;retry.hidden=false;suppress=true;window.NOWUP_CART160.restore391(accepted);suppress=false;last=JSON.stringify(payload(accepted));}finally{buttons();}});
 }
 retry.onclick=()=>schedule(true);window.addEventListener('nowup-cart-changed',()=>schedule());root.addEventListener('change',e=>{if(e.target.matches('[data-group192]'))refresh();});
 window.NOWUP_FASHION_STOCK391={async ready(){await queue;if(expires&&Date.now()>=expires){valid=false;label.textContent='Reserva expirada. Atualize para confirmar a disponibilidade.';retry.hidden=false;}buttons();return valid&&!pending;}};
 setInterval(()=>{if(valid&&expires&&Date.now()>=expires&&entries().length){valid=false;label.textContent='Reserva expirada. Atualize para confirmar a disponibilidade.';retry.hidden=false;buttons();}refresh();},15000);
 window.addEventListener('pageshow',refresh);document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh();});schedule(true);
})();
