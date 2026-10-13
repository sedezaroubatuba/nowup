(() => {
  'use strict';
  const root=document.querySelector('[data-native-menu]');
  if(!root||root.dataset.cartReady144)return;
  let cart=root.querySelector('[data-cart-dialog143]');
  if(!cart){
    const aside=root.querySelector('.menu-cart');
    if(!aside)return;
    cart=document.createElement('dialog');cart.className='nu143-cart-dialog';cart.dataset.cartDialog143='';
    cart.setAttribute('aria-label','Seu carrinho');root.append(cart);cart.append(aside);
    const heading=aside.querySelector('h2');if(heading)heading.textContent='Seu carrinho';
    const close=document.createElement('button');close.type='button';close.dataset.cartClose143='';close.textContent='×';close.setAttribute('aria-label','Fechar carrinho');aside.prepend(close);
    const summary=document.createElement('div');summary.className='nu143-summary';summary.innerHTML='<p><span>Subtotal</span><b data-cart-subtotal143></b></p><p><span>Entrega</span><b data-cart-fee143></b></p>';
    aside.querySelector('.cart-total')?.before(summary);
  }
  const items=cart?.querySelector('[data-cart-items]');
  const dock=root.querySelector('.nu83-cart-dock');
  if(!cart||!items||!dock)return;
  root.dataset.cartReady144='1';
  const dockText=dock.querySelector('strong');if(dockText&&dockText.firstChild?.nodeType===3)dockText.firstChild.textContent='Ver carrinho · ';
  const buy=document.createElement('button');buy.type='button';buy.className='nu144-continue';buy.textContent='Continuar comprando';buy.dataset.continueBuying144='';
  cart.querySelector('[data-checkout]')?.before(buy);
  let savedScroll=0;
  const closeCart=()=>{cart.close();window.scrollTo({top:savedScroll,behavior:'instant'});};
  buy.addEventListener('click',closeCart);
  cart.addEventListener('cancel',()=>{requestAnimationFrame(()=>window.scrollTo({top:savedScroll,behavior:'instant'}));});
  const checkout=root.querySelector('[data-checkout-dialog]');
  const receive=checkout?.querySelector('[data-fulfillment]');
  const total=cart.querySelector('[data-cart-total]');
  const sub=cart.querySelector('[data-cart-subtotal143]');
  const fee=cart.querySelector('[data-cart-fee143]');
  const money=n=>(n/100).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
  const cents=s=>Math.round(Number(String(s||'').replace(/[^\d,.-]/g,'').replace(/\./g,'').replace(',','.'))*100)||0;
  let scheduled=false;
  function refresh(){
    scheduled=false;
    items.querySelectorAll('.cart-item').forEach(row=>{
      if(row.querySelector('.nu143-product-thumb'))return;
      const control=row.querySelector('[data-minus], [data-cart-quantity], [data-remove]');
      const id=(control?.dataset.minus||control?.dataset.cartQuantity||control?.dataset.remove||'').split(':')[0];
      const product=[...root.querySelectorAll('[data-product]')].find(p=>p.dataset.id===id);
      const photo=product?.querySelector('img');
      const thumb=document.createElement(photo?'img':'span');
      thumb.className='nu143-product-thumb';
      if(photo){thumb.src=photo.src;thumb.alt='';thumb.addEventListener('error',()=>{thumb.replaceWith(Object.assign(document.createElement('span'),{className:'nu143-product-thumb',textContent:'🍽'}));},{once:true});}
      else{thumb.textContent='🍽';thumb.setAttribute('aria-hidden','true');}
      row.prepend(thumb);
      const name=row.querySelector('b')?.textContent||'produto';
      row.querySelector('[data-minus]')?.setAttribute('aria-label','Diminuir quantidade de '+name);
      row.querySelector('[data-plus]')?.setAttribute('aria-label','Aumentar quantidade de '+name);
      row.querySelector('[data-cart-quantity]')?.setAttribute('aria-label','Quantidade de '+name);
    });
    const hasItems=!!items.querySelector('.cart-item');
    dock.hidden=!hasItems;
    document.body.classList.toggle('nu143-has-cart',hasItems);
    const subtotal=cents(root.querySelector('[data-dock-total]')?.textContent);
    const grand=cents(checkout?.querySelector('[data-dialog-total]')?.textContent);
    sub.textContent=money(subtotal);fee.textContent=money(Math.max(0,grand-subtotal));total.textContent=money(grand);
    root.querySelectorAll('[data-receive143]').forEach(b=>{const active=b.dataset.receive143===receive?.value;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active));});
  }
  const schedule=()=>{if(!scheduled){scheduled=true;requestAnimationFrame(refresh);}};
  new MutationObserver(schedule).observe(items,{childList:true,subtree:true});
  const nativeTotal=checkout?.querySelector('[data-dialog-total]');
  if(nativeTotal)new MutationObserver(schedule).observe(nativeTotal,{childList:true,characterData:true,subtree:true});
  document.addEventListener('click',event=>{
    if(!dock.contains(event.target)||!event.target.closest('[data-cart-summary]'))return;
    event.preventDefault();event.stopImmediatePropagation();refresh();
    if(!cart.open){savedScroll=window.scrollY;cart.showModal();}
  },true);
  cart.querySelector('[data-cart-close143]')?.addEventListener('click',closeCart);
  cart.addEventListener('click',event=>{
    const button=event.target.closest('[data-receive143]');
    if(button&&receive){receive.value=button.dataset.receive143;receive.dispatchEvent(new Event('change',{bubbles:true}));schedule();}
    if(event.target===cart){const bounds=cart.getBoundingClientRect();if(event.clientX<bounds.left||event.clientX>bounds.right||event.clientY<bounds.top||event.clientY>bounds.bottom)closeCart();}
  });
  cart.querySelector('[data-checkout]')?.addEventListener('click',()=>{if(cart.open)cart.close();},true);
  window.addEventListener('nowup-cart-changed',schedule);
  refresh();
})();
