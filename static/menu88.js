(()=>{
  const root=document.querySelector('[data-native-menu]'); if(!root)return;
  const cfg=window.NOWUP_MENU||{},cart=new Map(),items=root.querySelector('[data-cart-items]'),total=root.querySelector('[data-cart-total]'),checkout=root.querySelector('[data-checkout]'),dialog=document.querySelector('[data-checkout-dialog]');
  if(!items||!total||!checkout||!dialog)return;
  const path=location.pathname.replace(/\/(?:menu|cardapio)\/?$/,'').replace(/\/$/,'');
  const customerId=Number.isSafeInteger(Number(cfg.customerId))&&Number(cfg.customerId)>0?Number(cfg.customerId):null;
  const key=cfg.whatsappCheckout?`nowup-cart:whatsapp257:u:${customerId}:${path}`:customerId?`nowup-cart:u:${customerId}:${path}`:`nowup-cart:${path}`;
  const infoKey=`nowup-cart-info:${cfg.whatsappCheckout?'whatsapp257:':''}${customerId?`u:${customerId}:`:''}${path}`;
  if(!customerId&&!cfg.demoBrowse386)return; // Only the explicit demo can simulate a local guest bag.
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
      if(window.NOWUP_FASHION_STOCK391&&!await window.NOWUP_FASHION_STOCK391.ready())return;
      if(cfg.demoBrowse386){window.alert('Demonstração: nenhum pedido real será enviado.');return;}
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
      let whatsappWindow390=null;
      if(cfg.whatsappCheckout){try{whatsappWindow390=window.open('about:blank','_blank');if(whatsappWindow390){whatsappWindow390.opener=null;whatsappWindow390.document.title='Preparando pedido';whatsappWindow390.document.body.textContent='Preparando seu pedido para abrir o WhatsApp…';}}catch(_){}}
      const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),30000);
      try{
        const response=await fetch(checkoutForm229.action,{method:'POST',body:new FormData(checkoutForm229),headers:{Accept:'application/json',...(document.getElementById('store-app256')?{'X-Nowup-Store-App':'256'}:{})},credentials:'same-origin',signal:controller.signal});
        const json=(response.headers.get('content-type')||'').includes('application/json')?await response.json():null;
        if(cfg.whatsappCheckout){
          const validWA=/^https:\/\/wa\.me\/55[0-9]{10,11}\?text=/.test(json?.whatsapp_url||'');
          if(!response.ok||!json?.prepared||!validWA)throw new Error(typeof json?.detail==='string'?json.detail:'Não foi possível preparar o pedido. Revise os dados.');
          if(json.recorded&&localStorage.getItem(key)===snapshot){cart.clear();localStorage.removeItem(key);localStorage.removeItem(infoKey);sessionStorage.removeItem('nowup-checkout247:'+key);render();}
          feedback.textContent='Pedido '+json.order_code+' preparado. Toque em Enviar no WhatsApp para a loja receber.';
          const old=checkoutForm229.querySelector('[data-whatsapp-ready257]');if(old){old.receiptCleanup?.();old.remove();}
          const ready=document.createElement('div');ready.dataset.whatsappReady257='';
          if(validWA){const link=document.createElement('a');link.className='btn primary full-btn';link.href=json.whatsapp_url;link.textContent='Abrir WhatsApp e enviar pedido';link.rel='noopener';link.target='_blank';ready.append(link);}
          const note=document.createElement('p');note.textContent='No WhatsApp, toque em Enviar. A loja confere e confirma seu pedido por lá. '+(json.payment_method==='pix'?'Aguarde a loja enviar o Pix e mande o comprovante na mesma conversa.':'Combine o pagamento com a loja na mesma conversa.')+' Você não precisa voltar ao link.';ready.append(note);
          checkoutForm229.append(ready);
          ready.scrollIntoView({block:'start',behavior:'smooth'});
          if(whatsappWindow390&&!whatsappWindow390.closed){whatsappWindow390.location.replace(json.whatsapp_url);whatsappWindow390=null;}
          return;
        }
        if(!response.ok||!json?.confirmed||json.path!==path||!((String(json.redirect||'').startsWith(path+'/pedido/')&&/^[A-Za-z0-9_-]+$/.test(String(json.redirect||'').slice((path+'/pedido/').length)))||/^\/pedido\/[A-Za-z0-9_-]+$/.test(json.redirect||'')))throw new Error(typeof json?.detail==='string'?json.detail:'Envio não confirmado. Confira Meus pedidos antes de tentar novamente.');
        // Clear this exact cart in the current page before navigating; no dependency
        // on cookies, tracking-page scripts or a back/forward cache restoration.
        if(localStorage.getItem(key)===snapshot){cart.clear();localStorage.removeItem(key);localStorage.removeItem(infoKey);sessionStorage.removeItem('nowup-checkout247:'+key);render();}
        feedback.textContent='Pedido enviado com sucesso.';
        location.assign(json.redirect);
      }catch(error){if(whatsappWindow390&&!whatsappWindow390.closed)whatsappWindow390.close();feedback.textContent=error.name==='AbortError'?'O envio demorou. Confira Meus pedidos antes de tentar novamente.':error.message;
      }finally{clearTimeout(timeout);checkoutForm229.dataset.submitting229='';if(button){button.disabled=false;button.textContent=original;}}
    });
    checkoutForm229.addEventListener('input',event=>{if(event.target.closest('[data-whatsapp-ready257]'))return;const old=checkoutForm229.querySelector('[data-whatsapp-ready257]');if(old){old.receiptCleanup?.();old.remove();}});
    window.addEventListener('pageshow',()=>{checkoutForm229.dataset.submitting229='';checkoutForm229.querySelectorAll('[type=submit]').forEach(b=>b.disabled=false);});
  }
  const cartField=dialog.querySelector('[data-cart-json]'),dialogTotal=dialog.querySelector('[data-dialog-total]'),fulfillment=dialog.querySelector('[data-fulfillment]'),payment=dialog.querySelector('[data-payment]'),dockTotal=root.querySelector('[data-dock-total]'),cartCount=root.querySelector('[data-cart-count]'),dockCheckout=root.querySelector('[data-dock-checkout]');
  document.addEventListener("DOMContentLoaded",()=>render(),{once:true});
  const qty=v=>Math.max(1,Math.min(99,parseInt(v,10)||1));
  function added366(card){window.NOWUP_CART_BAG366?.added(card);}
  function card366(id){return [...root.querySelectorAll('[data-product]')].find(card=>Number(card.dataset.id)===Number(id));}
  function baseSubtotal(){let sum=0;cart.forEach(v=>sum+=v.unitPrice*v.quantity);return sum}
  function fee(){if(fulfillment?.value!=='delivery')return 0;const zone=dialog.querySelector('[data-delivery-zone265]');return zone?Number(zone.selectedOptions[0]?.dataset.fee||0):Number(cfg.deliveryFee||0)}
  function save(){try{localStorage.setItem(key,JSON.stringify([...cart]));localStorage.setItem(infoKey,JSON.stringify({name:cfg.storeName||'',updated:Date.now()}));window.dispatchEvent(new Event('nowup-cart-changed'));}catch(_){}}
  function sync(){if(cartField)cartField.value=JSON.stringify([...cart].map(([,v])=>({id:v.productId,quantity:v.quantity,...(v.weightGrams370?{weight_grams370:v.weightGrams370}:{}),notes:v.notes||'',options:v.options.map(o=>({id:Number(o.id),quantity:o.quantity||1})),utensils:!!v.utensils,customization:v.customization||{removed:[],groups:{}}})));save()}
  const notesAllowed=v=>{const card=[...root.querySelectorAll('[data-product]')].find(p=>Number(p.dataset.id)===v.productId);try{return JSON.parse(card?.dataset.custom192||'null')?.notes!==false;}catch(_){return true;}};
  const isPersonalized=v=>[...root.querySelectorAll('[data-product]')].some(p=>Number(p.dataset.id)===v.productId&&p.dataset.dish==='1');
  function comboDescription305(v,card){
    let config={};try{config=JSON.parse(card?.dataset.custom192||'{}');}catch(_){}
    const entries=config.combo_items||[],groups=config.groups||[];
    const principal=entries.find(i=>i.principal)||entries.find(i=>i.quantity===1&&groups.find(g=>g.id===i.group_id301)?.options?.length===1);
    let short=config.combo_notice316?`<p style="white-space:pre-wrap"><strong>Aviso do combo:</strong> ${esc(config.combo_notice316)}</p>`:'';
    if(principal)short+=`<small class="nu305-principal">Principal: ${esc(principal.quantity)} × ${esc(principal.name)}</small>`;
    const included=entries.filter(i=>i!==principal).map(i=>`${i.quantity} × ${groups.find(g=>g.id===i.group_id301)?.name||i.name}`);
    if(included.length)short+=`<small>${esc(included.join(' · '))}</small>`;
    if(config.combo_manual?.length)short+=`<small>Incluídos: ${esc(config.combo_manual.map(i=>i.name).join(', '))}</small>`;
    const full=v.customizationSummary||(window.NOWUP_CUSTOM192&&card?window.NOWUP_CUSTOM192.describe(card,v.customization):'');
    const manual=(config.combo_manual||[]).map(i=>i.quantity+' × '+i.name).join(', ');
    const extras=(v.options||[]).map(o=>o.name).join(', ');
    const detail=[full,extras,manual].filter(Boolean).map(t=>`<p>${esc(t)}</p>`).join('');
    if(detail)short+=`<details class="nu305-combo-details"><summary>Ver itens escolhidos</summary><div>${detail}</div></details>`;
    return `<div class="nu305-combo-summary">${short}</div>`;
  }
  function render(){window.NOWUP_SAVINGS315?.render([...cart.values()],root,dialog);checkoutForm229?.querySelector('[data-whatsapp-ready257]')?.remove();let html='';cart.forEach((v,id)=>{const card=[...root.querySelectorAll('[data-product]')].find(p=>Number(p.dataset.id)===v.productId),combo=card?.dataset.combo256==='1'||card?.dataset.unitCombo364==='1';const description=combo?comboDescription305(v,card):`${v.utensils?'<small>🍴 Enviar talheres (garfo e faca)</small>':''}${v.customizationSummary?`<small>${esc(v.customizationSummary)}</small>`:''}${v.options.length?`<small>${v.options.map(o=>esc(o.name)).join(', ')}</small>`:''}`;html+=`<div class="cart-item ${combo?'nu305-combo-cart':''}"><div><b>${esc(v.name)}</b><span class="nu305-line-price">${money(v.unitPrice*v.quantity)}</span>${description}${v.quantity>1?`<small>${v.quantity} × ${money(v.unitPrice)}</small>`:''}${isPersonalized(v)?`<button type="button" class="nu160-edit" data-edit-personalization160="${id}">${combo?'Editar combo':'Editar personalização'}</button>`:''}<input ${notesAllowed(v)?'':'hidden disabled'} class="cart-note" data-note="${id}" maxlength="300" value="${esc(v.notes||'')}" placeholder="Observação (opcional)"></div><div class="cart-quantity">${v.weightGrams370?`<button type="button" data-edit-weight370="${v.productId}">Alterar peso</button><input type="hidden" data-cart-quantity="${id}" value="1">`:`<button type="button" data-minus="${id}">−</button><input type="number" min="1" max="${v.max||99}" value="${v.quantity}" data-cart-quantity="${id}"><button type="button" data-plus="${id}">+</button>`}<button class="cart-remove" type="button" data-remove="${id}">Excluir</button></div></div>`});
    items.innerHTML=html||'<p class="muted">Adicione produtos para começar.</p>';const sub=baseSubtotal(),grand=sub+fee(),count=[...cart.values()].reduce((sum,v)=>sum+v.quantity,0);total.textContent=money(sub);if(dialogTotal)dialogTotal.textContent=money(grand);if(dockTotal)dockTotal.textContent=money(sub);if(cartCount)cartCount.textContent=count+` ${count===1?'item':'itens'}`;checkout.disabled=cart.size>50||cfg.ownerView||cfg.open===false||!cart.size||sub<Number(cfg.minimumOrder||0)||[...cart.values()].some(v=>v.options.length>20||v.options.some(o=>(o.quantity||1)!==1));if(dockCheckout)dockCheckout.disabled=checkout.disabled;checkout.textContent=cart.size>50?'Limite de 50 itens diferentes por pedido':[...cart.values()].some(v=>v.options.length>20||v.options.some(o=>(o.quantity||1)!==1))?'Atualize os adicionais: até 3, uma porção de cada':cfg.open===false?'Pedidos pausados':cart.size&&sub<Number(cfg.minimumOrder||0)?`Faltam ${money(Number(cfg.minimumOrder)-sub)} para o mínimo`:'Continuar pedido';const note=dialog.querySelector('[data-fee-note]');if(note)note.textContent=fee()?`(inclui ${money(fee())} de entrega)`:'';sync()}
  if(!customerId)try{if(localStorage.getItem(key)===null){const legacy=localStorage.getItem(key+'/menu');if(legacy!==null){localStorage.setItem(key,legacy);localStorage.removeItem(key+'/menu');}}}catch(_){}
  try{(JSON.parse(localStorage.getItem(key)||'[]')||[]).forEach(([id,v])=>{if(v&&v.name)cart.set(String(id),{...v,productId:Number(v.productId||String(id).split(':')[0]),unitPrice:Number(v.unitPrice||v.price||0),options:Array.isArray(v.options)?v.options:[],max:Number(v.max||99)})})}catch(_){localStorage.removeItem(key)}
  window.NOWUP_CART160={
    restore391(rows){cart.clear();for(const {id,...v} of rows)cart.set(id,v);render();},
    removeProduct(productId){for(const [id,v] of cart)if(Number(v.productId)===Number(productId))cart.delete(id);render();},
    entries389(){return [...cart].map(([id,v])=>({id,...JSON.parse(JSON.stringify(v))}));},
    quantity(productId){return [...cart.values()].filter(v=>Number(v.productId)===Number(productId)).reduce((sum,v)=>sum+(Number(v.quantity)||0),0);},
    setWeight(card,grams){
      if(cfg.ownerView||cfg.open===false||card.dataset.weight370!=='1'||card.querySelector('[data-add]')?.disabled)throw new Error('Produto indisponível.');
      if(!Number.isSafeInteger(grams)||grams<100||grams>99900||grams%100)throw new Error('Escolha um peso válido.');
      const rate=Number(card.dataset.price),unitPrice=Math.floor((rate*grams+500)/1000);
      if(!Number.isSafeInteger(rate)||rate<1||rate>10000000)throw new Error('Preço indisponível.');
      const id=card.dataset.id+':weight370';
      const existing=[...cart].filter(([,v])=>v.productId===Number(card.dataset.id)&&v.weightGrams370);
      existing.forEach(([old])=>cart.delete(old));
      const label=grams>=1000?(grams/1000).toLocaleString('pt-BR')+' kg ('+grams.toLocaleString('pt-BR')+' g)':grams+' g';
      cart.set(id,{productId:Number(card.dataset.id),name:card.dataset.name+' — '+label,unitPrice,quantity:1,notes:existing[0]?.[1]?.notes||'',options:[],max:1,weightGrams370:grams});render();added366(card);
    },
    weight(productId){return [...cart.values()].find(v=>v.productId===Number(productId)&&v.weightGrams370)?.weightGrams370||0;},
    adjust(productId,delta){
      if(card366(productId)?.dataset.weight370==='1'){window.NOWUP_WEIGHT370?.open(card366(productId));return;}
      if(cfg.ownerView||![-1,1].includes(delta))return;
      const matches=[...cart].filter(([,v])=>Number(v.productId)===Number(productId));
      const entry=matches[matches.length-1];if(!entry)return;
      const [id,value]=entry;
      if(delta>0&&(cfg.open===false||value.quantity>=Number(value.max||99)))return;
      if(delta>0&&window.NOWUP_FASHION389){try{window.NOWUP_FASHION389.validate(card366(productId),Array.from({length:value.quantity+1},()=>({customization:value.customization})),id);}catch(err){alert(err.message);return;}}
      value.quantity+=delta;if(value.quantity<=0)cart.delete(id);render();if(delta>0)added366(card366(productId));
    },
    get(id){const v=cart.get(id);return v?JSON.parse(JSON.stringify(v)):null;},
    commit(card,configs,replaceId=null){
      if(cfg.ownerView)throw new Error('Sua loja está em modo de visualização.');
      window.NOWUP_FASHION389?.validate(card,configs,replaceId);
      const draft=new Map([...cart].map(([id,v])=>[id,{...v,options:v.options.map(o=>({...o}))}]));
      if(replaceId&&!draft.has(replaceId))throw new Error('Este item mudou. Reabra o carrinho.');
      if(replaceId)draft.delete(replaceId);
      const max=Number(card.dataset.max)||99;
      if(configs.some(c=>!c||c.options.length>window.NOWUP_CUSTOM192.limit(card)))throw new Error('Confira os adicionais de cada lanche.');
      for(const config of configs){
        window.NOWUP_CUSTOM192.validate(card,config);
        const notes=String(config.notes||'').trim(),options=config.options||[],utensils=!!config.utensils,customization=config.customization||{removed:[],groups:{}},customizationSummary=window.NOWUP_CUSTOM192.describe(card,customization);
        const id=`${card.dataset.id}:${options.map(o=>o.id).sort().join('-')}:utensils${utensils?1:0}:notes${encodeURIComponent(notes)}:custom${encodeURIComponent(JSON.stringify(customization))}`;
        const unitPrice=Number(card.dataset.price)+options.reduce((sum,o)=>sum+Number(o.price),0)+(window.NOWUP_CUSTOM192.extraPrice364?.(card,customization)||0);
        const old=draft.get(id)||{productId:Number(card.dataset.id),name:card.dataset.name,unitPrice,quantity:0,notes,options,max,utensils,customization,customizationSummary};
        if(old.quantity+1>max)throw new Error('Limite de unidades deste produto atingido.');
        old.quantity++;old.unitPrice=unitPrice;draft.set(id,old);
      }
      cart.clear();draft.forEach((v,id)=>cart.set(id,v));render();if(!replaceId&&configs.length)added366(card);
    }
  };
  root.addEventListener('click',e=>{const b=e.target.closest('[data-add]');if(!b||b.disabled||cfg.ownerView)return;const card=b.closest('[data-product]');if(!card)return;if(card.dataset.weight370==='1'){window.NOWUP_WEIGHT370?.open(card);return;}const itemNotes=card.querySelector('[data-product-notes]')?.value||'';const options=[...card.querySelectorAll('[data-product-option]:checked')].map(o=>({id:o.value,name:o.dataset.optionName,price:Number(o.dataset.optionPrice||0)}));const utensils=!!card.querySelector('[data-utensils158]')?.checked;const id=`${card.dataset.id}:${options.map(o=>o.id).sort().join('-')}:utensils${utensils?1:0}:notes${encodeURIComponent(itemNotes.trim())}`,amount=card.dataset.dish==='1'?1:qty(card.querySelector('[data-product-quantity]')?.value),unitPrice=Number(card.dataset.price)+options.reduce((s,o)=>s+o.price,0),current=cart.get(id)||{productId:Number(card.dataset.id),name:card.dataset.name,unitPrice,quantity:0,notes:'',options,max:Number(card.dataset.max||99)};current.utensils=utensils;current.notes=itemNotes;const previous366=current.quantity;current.quantity=Math.min(current.max||99,current.quantity+amount);cart.set(id,current);b.textContent='Adicionado ✓';setTimeout(()=>b.textContent='Adicionar',800);render();if(current.quantity>previous366)added366(card)});
  items.addEventListener('click',e=>{const id=e.target.dataset.plus||e.target.dataset.minus||e.target.dataset.remove;if(!id)return;if(e.target.dataset.remove){cart.delete(id);render();return}const v=cart.get(id),previous366=v.quantity;if(e.target.dataset.plus&&window.NOWUP_FASHION389){try{window.NOWUP_FASHION389.validate(card366(v.productId),Array.from({length:v.quantity+1},()=>({customization:v.customization})),id);}catch(err){alert(err.message);return;}}v.quantity=Math.min(v.max||99,v.quantity+(e.target.dataset.plus?1:-1));if(v.quantity<1)cart.delete(id);render();if(v.quantity>previous366)added366(card366(v.productId))});
  items.addEventListener('input',e=>{const id=e.target.dataset.note||e.target.dataset.cartQuantity;if(!id||!cart.has(id))return;if(e.target.dataset.note!==undefined)cart.get(id).notes=e.target.value;else{const v=cart.get(id),before=v.quantity;v.quantity=Math.min(v.max||99,qty(e.target.value));if(v.quantity>before)added366(card366(v.productId));}sync()});items.addEventListener('change',render);
  let category='all';
  const search=root.querySelector('[data-product-search]');
  const normalize=value=>String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  const filter=()=>root.querySelectorAll('[data-product]').forEach(p=>p.hidden=(category!=='all'&&p.dataset.category!==category)||!normalize(p.dataset.name+' '+p.textContent).includes(normalize(search?.value)));
  root.querySelectorAll('[data-category-filter]').forEach(b=>b.addEventListener('click',()=>{category=b.dataset.categoryFilter;root.querySelectorAll('[data-category-filter]').forEach(x=>x.classList.toggle('active',x===b));filter();}));
  search?.addEventListener('input',filter);
  root.querySelector('[data-cart-summary]')?.addEventListener('click',()=>{const summary=root.querySelector('.menu-cart');summary?.scrollIntoView({behavior:'smooth',block:'center'});summary?.focus({preventScroll:true});});
  function openOrderDialog353(target){
    // Keep order dialogs outside catalogue sections that can be hidden by filters.
    if(target.parentElement!==root)root.append(target);
    target.hidden=false;target.classList.add('nu353-order-dialog');
    if(!target.open)target.showModal();target.scrollTop=0;
  }
  window.NOWUP_OPEN_ORDER353=openOrderDialog353;
  checkout.addEventListener('click',()=>openOrderDialog353(dialog));dockCheckout?.addEventListener('click',()=>{if(!checkout.disabled)openOrderDialog353(dialog)});dialog.querySelector('[data-dialog-close]')?.addEventListener('click',()=>dialog.close());
  function checkoutFields(){const delivery=fulfillment?.value==='delivery',address=dialog.querySelector('[data-address]');if(address){address.hidden=!delivery;address.querySelectorAll('input,select').forEach(i=>i.required=delivery&&['address','neighborhood'].includes(i.name))}const change=dialog.querySelector('[data-change]');if(change)change.hidden=payment?.value!=='cash';render()}
  dialog.querySelector('[data-delivery-zone265]')?.addEventListener('change',render);
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


