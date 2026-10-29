(()=>{
  const root=document.querySelector('[data-native-menu]'); if(!root)return;
  const cfg=window.NOWUP_MENU||{},cart=new Map(),items=root.querySelector('[data-cart-items]'),total=root.querySelector('[data-cart-total]'),checkout=root.querySelector('[data-checkout]'),dialog=document.querySelector('[data-checkout-dialog]');
  if(!items||!total||!checkout||!dialog)return;
  const path=location.pathname.replace(/\/menu\/?$/,'').replace(/\/$/,'');
  const customerId=Number.isSafeInteger(Number(cfg.customerId))&&Number(cfg.customerId)>0?Number(cfg.customerId):null;
  const key=customerId?`nowup-cart:u:${customerId}:${path}`:`nowup-cart:${path}`;
  const infoKey=`nowup-cart-info:${customerId?`u:${customerId}:`:''}${path}`;
  if(!customerId)return; // Browsing is public; cart mutations require a customer session.
  // A confirmação do servidor limpa também o carrinho de quem comprou sem conta.
  const completed=document.cookie.match(/(?:^|;\s*)nowup_cart_completed=([^;]+)/);
  if(completed){try{const slug=decodeURIComponent(completed[1]);if(path.endsWith('/p/'+slug)){localStorage.removeItem(key);localStorage.removeItem(infoKey);document.cookie='nowup_cart_completed=; Max-Age=0; Path=/';}}catch(_){}}
  const money=c=>(c/100).toLocaleString('pt-BR',{style:'currency',currency:'BRL'}),esc=v=>String(v).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  const checkoutForm229=dialog.querySelector('form');
  if(checkoutForm229){
    const requestInput=document.createElement('input');requestInput.type='hidden';requestInput.name='request_key';checkoutForm229.append(requestInput);
    let lastPayload='',token='';
    checkoutForm229.addEventListener('submit',async event=>{
      event.preventDefault();
      if(checkoutForm229.dataset.submitting229==='1')return;
      const fields=[...new FormData(checkoutForm229)].filter(([name])=>name!=='request_key');const payload=JSON.stringify(fields);
      const snapshot=localStorage.getItem(key);
      if(window.NOWUP_CHECKOUT247){token=window.NOWUP_CHECKOUT247.prepare(key,payload,snapshot);lastPayload=payload;}
      else if(!token||payload!==lastPayload){token=crypto.randomUUID();lastPayload=payload;}
      requestInput.value=token;
      checkoutForm229.dataset.submitting229='1';
      let feedback=checkoutForm229.querySelector('[data-checkout-feedback251]');
      if(!feedback){feedback=document.createElement('p');feedback.dataset.checkoutFeedback251='';feedback.setAttribute('role','status');checkoutForm229.append(feedback);}
      const button=event.submitter,original=button?.textContent;
      if(button){button.disabled=true;button.textContent='Enviando pedido…';}
      feedback.textContent='Enviando pedido…';
      const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),30000);
      try{
        const response=await fetch(checkoutForm229.action,{method:'POST',body:new FormData(checkoutForm229),headers:{Accept:'application/json',...(document.getElementById('store-app256')?{'X-Nowup-Store-App':'256'}:{})},credentials:'same-origin',signal:controller.signal});
        const json=(response.headers.get('content-type')||'').includes('application/json')?await response.json():null;
        if(!response.ok||!json?.confirmed||json.path!==path||!((String(json.redirect||'').startsWith(path+'/pedido/')&&/^[A-Za-z0-9_-]+$/.test(String(json.redirect||'').slice((path+'/pedido/').length)))||/^\/pedido\/[A-Za-z0-9_-]+$/.test(json.redirect||'')))throw new Error(typeof json?.detail==='string'?json.detail:'Envio não confirmado. Confira Meus pedidos antes de tentar novamente.');
        // Clear this exact cart in the current page before navigating; no dependency
        // on cookies, tracking-page scripts or a back/forward cache restoration.
        if(localStorage.getItem(key)===snapshot){cart.clear();localStorage.removeItem(key);localStorage.removeItem(infoKey);sessionStorage.removeItem('nowup-checkout247:'+key);render();}
        feedback.textContent='Pedido enviado com sucesso.';
        location.assign(json.redirect);
      }catch(error){feedback.textContent=error.name==='AbortError'?'O envio demorou. Confira Meus pedidos antes de tentar novamente.':error.message;
      }finally{clearTimeout(timeout);checkoutForm229.dataset.submitting229='';if(button){button.disabled=false;button.textContent=original;}}
    });
    window.addEventListener('pageshow',()=>{checkoutForm229.dataset.submitting229='';checkoutForm229.querySelectorAll('[type=submit]').forEach(b=>b.disabled=false);});
  }
  const cartField=dialog.querySelector('[data-cart-json]'),dialogTotal=dialog.querySelector('[data-dialog-total]'),fulfillment=dialog.querySelector('[data-fulfillment]'),payment=dialog.querySelector('[data-payment]'),dockTotal=root.querySelector('[data-dock-total]'),cartCount=root.querySelector('[data-cart-count]'),dockCheckout=root.querySelector('[data-dock-checkout]');
  const qty=v=>Math.max(1,Math.min(99,parseInt(v,10)||1));
  function baseSubtotal(){let sum=0;cart.forEach(v=>sum+=v.unitPrice*v.quantity);return sum}
  function fee(){return fulfillment?.value==='delivery'?Number(cfg.deliveryFee||0):0}
  function save(){try{localStorage.setItem(key,JSON.stringify([...cart]));localStorage.setItem(infoKey,JSON.stringify({name:cfg.storeName||'',updated:Date.now()}));window.dispatchEvent(new Event('nowup-cart-changed'));}catch(_){}}
  function sync(){if(cartField)cartField.value=JSON.stringify([...cart].map(([,v])=>({id:v.productId,quantity:v.quantity,notes:v.notes||'',options:v.options.map(o=>({id:Number(o.id),quantity:o.quantity||1})),utensils:!!v.utensils,customization:v.customization||{removed:[],groups:{}}})));save()}
  const notesAllowed=v=>{const card=[...root.querySelectorAll('[data-product]')].find(p=>Number(p.dataset.id)===v.productId);try{return JSON.parse(card?.dataset.custom192||'null')?.notes!==false;}catch(_){return true;}};
  const isPersonalized=v=>[...root.querySelectorAll('[data-product]')].some(p=>Number(p.dataset.id)===v.productId&&p.dataset.dish==='1');
  function render(){let html='';cart.forEach((v,id)=>{html+=`<div class="cart-item"><div><b>${esc(v.name)}</b>${v.utensils?'<small>🍴 Enviar talheres (garfo e faca)</small>':''}${v.customizationSummary?`<small>${esc(v.customizationSummary)}</small>`:''}${v.options.length?`<small>${v.options.map(o=>esc(o.name)).join(', ')}</small>`:''}<small>${money(v.unitPrice)} por unidade</small><small class="nu150-item-total">Total do item: ${money(v.unitPrice*v.quantity)}</small>${isPersonalized(v)?`<button type="button" class="nu160-edit" data-edit-personalization160="${id}">Editar personalização</button>`:''}<input ${notesAllowed(v)?'':'hidden disabled'} class="cart-note" data-note="${id}" maxlength="300" value="${esc(v.notes||'')}" placeholder="Observação: bem passado, sem feijão..."></div><div class="cart-quantity"><button type="button" data-minus="${id}">−</button><input type="number" min="1" max="${v.max||99}" value="${v.quantity}" data-cart-quantity="${id}"><button type="button" data-plus="${id}">+</button><button class="cart-remove" type="button" data-remove="${id}">Excluir</button></div></div>`});
    items.innerHTML=html||'<p class="muted">Adicione produtos para começar.</p>';const sub=baseSubtotal(),grand=sub+fee(),count=[...cart.values()].reduce((sum,v)=>sum+v.quantity,0);total.textContent=money(sub);if(dialogTotal)dialogTotal.textContent=money(grand);if(dockTotal)dockTotal.textContent=money(sub);if(cartCount)cartCount.textContent=count+` ${count===1?'item':'itens'}`;checkout.disabled=cart.size>50||cfg.ownerView||cfg.open===false||!cart.size||sub<Number(cfg.minimumOrder||0)||[...cart.values()].some(v=>v.options.length>20||v.options.some(o=>(o.quantity||1)!==1));if(dockCheckout)dockCheckout.disabled=checkout.disabled;checkout.textContent=cart.size>50?'Limite de 50 itens diferentes por pedido':[...cart.values()].some(v=>v.options.length>20||v.options.some(o=>(o.quantity||1)!==1))?'Atualize os adicionais: até 3, uma porção de cada':cfg.open===false?'Pedidos pausados':cart.size&&sub<Number(cfg.minimumOrder||0)?`Faltam ${money(Number(cfg.minimumOrder)-sub)} para o mínimo`:'Continuar pedido';const note=dialog.querySelector('[data-fee-note]');if(note)note.textContent=fee()?`(inclui ${money(fee())} de entrega)`:'';sync()}
  if(!customerId)try{if(localStorage.getItem(key)===null){const legacy=localStorage.getItem(key+'/menu');if(legacy!==null){localStorage.setItem(key,legacy);localStorage.removeItem(key+'/menu');}}}catch(_){}
  try{(JSON.parse(localStorage.getItem(key)||'[]')||[]).forEach(([id,v])=>{if(v&&v.name)cart.set(String(id),{...v,productId:Number(v.productId||String(id).split(':')[0]),unitPrice:Number(v.unitPrice||v.price||0),options:Array.isArray(v.options)?v.options:[],max:Number(v.max||99)})})}catch(_){localStorage.removeItem(key)}
  window.NOWUP_CART160={
    get(id){const v=cart.get(id);return v?JSON.parse(JSON.stringify(v)):null;},
    commit(card,configs,replaceId=null){
      if(cfg.ownerView)throw new Error('Sua loja está em modo de visualização.');
      const draft=new Map([...cart].map(([id,v])=>[id,{...v,options:v.options.map(o=>({...o}))}]));
      if(replaceId&&!draft.has(replaceId))throw new Error('Este item mudou. Reabra o carrinho.');
      if(replaceId)draft.delete(replaceId);
      const max=Number(card.dataset.max)||99;
      if(configs.some(c=>!c||c.options.length>window.NOWUP_CUSTOM192.limit(card)))throw new Error('Confira os adicionais de cada lanche.');
      for(const config of configs){
        window.NOWUP_CUSTOM192.validate(card,config);
        const notes=String(config.notes||'').trim(),options=config.options||[],utensils=!!config.utensils,customization=config.customization||{removed:[],groups:{}},customizationSummary=window.NOWUP_CUSTOM192.describe(card,customization);
        const id=`${card.dataset.id}:${options.map(o=>o.id).sort().join('-')}:utensils${utensils?1:0}:notes${encodeURIComponent(notes)}:custom${encodeURIComponent(JSON.stringify(customization))}`;
        const unitPrice=Number(card.dataset.price)+options.reduce((sum,o)=>sum+Number(o.price),0);
        const old=draft.get(id)||{productId:Number(card.dataset.id),name:card.dataset.name,unitPrice,quantity:0,notes,options,max,utensils,customization,customizationSummary};
        if(old.quantity+1>max)throw new Error('Limite de unidades deste produto atingido.');
        old.quantity++;old.unitPrice=unitPrice;draft.set(id,old);
      }
      cart.clear();draft.forEach((v,id)=>cart.set(id,v));render();
    }
  };
  root.addEventListener('click',e=>{const b=e.target.closest('[data-add]');if(!b||b.disabled||cfg.ownerView)return;const card=b.closest('[data-product]');if(!card)return;const itemNotes=card.querySelector('[data-product-notes]')?.value||'';const options=[...card.querySelectorAll('[data-product-option]:checked')].map(o=>({id:o.value,name:o.dataset.optionName,price:Number(o.dataset.optionPrice||0)}));const utensils=!!card.querySelector('[data-utensils158]')?.checked;const id=`${card.dataset.id}:${options.map(o=>o.id).sort().join('-')}:utensils${utensils?1:0}:notes${encodeURIComponent(itemNotes.trim())}`,amount=card.dataset.dish==='1'?1:qty(card.querySelector('[data-product-quantity]')?.value),unitPrice=Number(card.dataset.price)+options.reduce((s,o)=>s+o.price,0),current=cart.get(id)||{productId:Number(card.dataset.id),name:card.dataset.name,unitPrice,quantity:0,notes:'',options,max:Number(card.dataset.max||99)};current.utensils=utensils;current.notes=itemNotes;current.quantity=Math.min(current.max||99,current.quantity+amount);cart.set(id,current);b.textContent='Adicionado ✓';setTimeout(()=>b.textContent='Adicionar',800);render()});
  items.addEventListener('click',e=>{const id=e.target.dataset.plus||e.target.dataset.minus||e.target.dataset.remove;if(!id)return;if(e.target.dataset.remove){cart.delete(id);render();return}const v=cart.get(id);v.quantity=Math.min(v.max||99,v.quantity+(e.target.dataset.plus?1:-1));if(v.quantity<1)cart.delete(id);render()});
  items.addEventListener('input',e=>{const id=e.target.dataset.note||e.target.dataset.cartQuantity;if(!id||!cart.has(id))return;if(e.target.dataset.note!==undefined)cart.get(id).notes=e.target.value;else cart.get(id).quantity=Math.min(cart.get(id).max||99,qty(e.target.value));sync()});items.addEventListener('change',render);
  let category='all';
  const search=root.querySelector('[data-product-search]');
  const normalize=value=>String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  const filter=()=>root.querySelectorAll('[data-product]').forEach(p=>p.hidden=(category!=='all'&&p.dataset.category!==category)||!normalize(p.dataset.name+' '+p.textContent).includes(normalize(search?.value)));
  root.querySelectorAll('[data-category-filter]').forEach(b=>b.addEventListener('click',()=>{category=b.dataset.categoryFilter;root.querySelectorAll('[data-category-filter]').forEach(x=>x.classList.toggle('active',x===b));filter();}));
  search?.addEventListener('input',filter);
  root.querySelector('[data-cart-summary]')?.addEventListener('click',()=>{const summary=root.querySelector('.menu-cart');summary?.scrollIntoView({behavior:'smooth',block:'center'});summary?.focus({preventScroll:true});});
  checkout.addEventListener('click',()=>dialog.showModal());dockCheckout?.addEventListener('click',()=>{if(!checkout.disabled)dialog.showModal()});dialog.querySelector('[data-dialog-close]')?.addEventListener('click',()=>dialog.close());
  function checkoutFields(){const delivery=fulfillment?.value==='delivery',address=dialog.querySelector('[data-address]');if(address){address.hidden=!delivery;address.querySelectorAll('input').forEach(i=>i.required=delivery)}const change=dialog.querySelector('[data-change]');if(change)change.hidden=payment?.value!=='cash';render()}
  fulfillment?.addEventListener('change',checkoutFields);payment?.addEventListener('change',checkoutFields);// Cart is cleared only after the server confirms a successfully created order.
  const slides=[...root.querySelectorAll('.nu-daily-slide')],dots=[...root.querySelectorAll('[data-promo-index]')];let promoIndex=0;const showPromo=i=>{promoIndex=i;slides.forEach((s,n)=>s.classList.toggle('active',n===i));dots.forEach((d,n)=>d.classList.toggle('active',n===i))};dots.forEach((d,i)=>d.addEventListener('click',()=>showPromo(i)));if(slides.length>1)setInterval(()=>showPromo((promoIndex+1)%slides.length),4000);
  root.querySelector('[data-show-all]')?.addEventListener('click',()=>{root.querySelectorAll('[data-category-filter]').forEach((x,i)=>x.classList.toggle('active',i===0));root.querySelectorAll('[data-product]').forEach(p=>p.hidden=false)});
  function restore200(){
    try{const stored=JSON.parse(localStorage.getItem(key)||'[]');cart.clear();stored.forEach(([id,v])=>cart.set(id,v));render();}catch(_){}
  }
  window.addEventListener('pageshow',()=>restore200());
  window.addEventListener('storage',e=>{if(e.key===key)restore200();});
  window.addEventListener('nowup-cart-confirmed247',e=>{if(e.detail?.key===key)restore200();});
  if(cfg.ownerView){root.querySelectorAll('[data-add], [data-product-quantity]').forEach(e=>{e.disabled=true;});}
  checkoutFields();render();
})();

