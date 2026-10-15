/* V190: compact category pages use the existing cart, product and option nodes. */
document.addEventListener('DOMContentLoaded',()=>{
 'use strict';
 const body=document.body,root=document.querySelector('[data-native-menu]');
 const template=document.getElementById('nu187-store-template');
 const heading=root?.querySelector('.nu83-catalog-heading'),layout=root?.querySelector('.menu-layout');
 const search=heading?.querySelector('[data-product-search], [data-store-search]');
 if(!root||!template||!heading||!layout||!search){body.classList.remove('nu187-store-home');return;}
 const make=(tag,cls,text)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;};
 const intro=template.content.firstElementChild.cloneNode(true),nav=root.querySelector('.menu-category-nav');
 const sticky=root.querySelector('.nu-menu-sticky')||heading.parentElement;
 const anchor=document.createComment('store190');layout.before(anchor);anchor.before(intro);
 const showcase=make('div','nu190-showcase');layout.before(showcase);
 const originals=Array.from(layout.querySelectorAll('[data-product]')),sections=new Map(),refreshers=[],cartRefreshers=[];
 const back=make('button','nu187-back','←');back.type='button';heading.prepend(back);
 let homeScroll=0;
 const money=cents=>(cents/100).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
 const resize=()=>window.dispatchEvent(new Event('resize'));
 function showProducts(focus=false){
  if(body.classList.contains('nu187-store-home'))homeScroll=window.scrollY;
  intro.hidden=true;showcase.hidden=true;back.setAttribute('aria-label','Voltar às informações da loja');
  if(nav)sticky.append(nav);body.classList.remove('nu187-store-home');search.placeholder='Buscar nesta loja';
  resize();window.scrollTo({top:0,behavior:'instant'});if(focus)search.focus({preventScroll:true});
 }
 function showHome(){
  intro.hidden=false;showcase.hidden=false;body.classList.add('nu187-store-home');back.setAttribute('aria-label','Voltar ao início do NowUp');
  if(nav)anchor.after(nav);search.value='';search.dispatchEvent(new Event('input',{bubbles:true}));search.placeholder='Pesquisar produtos';search.blur();
  refreshers.forEach(fn=>fn());cartRefreshers.forEach(fn=>fn());resize();window.scrollTo({top:homeScroll,behavior:'instant'});
 }
 function compact(card){
  const item=make('article','nu190-card'),image=card.querySelector('.nu163-media img, img');
  if(image){const photo=make('img');photo.src=image.currentSrc||image.getAttribute('src');photo.alt='';photo.loading='lazy';photo.addEventListener('error',()=>{photo.src='/static/product-placeholder.svg';},{once:true});item.append(photo);}
  else item.append(make('div','nu190-no-image','🍽'));
  const content=make('div','nu190-card-content');content.append(make('h3','',card.dataset.name||card.querySelector('h3')?.textContent||'Produto'),make('strong','',money(Number(card.dataset.price)||0)));
  const add=make('button','nu190-add','Adicionar');add.type='button';
  const controls=make('div','nu190-amount'),minus=make('button','','−'),plus=make('button','','+'),amount=make('input');
  minus.type=plus.type='button';minus.setAttribute('aria-label','Diminuir '+card.dataset.name);plus.setAttribute('aria-label','Aumentar '+card.dataset.name);
  amount.type='number';amount.min='0';amount.step='1';amount.inputMode='numeric';amount.setAttribute('aria-label','Quantidade de '+card.dataset.name);controls.append(minus,amount,plus);
  function key(){const opts=Array.from(card.querySelectorAll('[data-product-option]:checked')).map(o=>o.value).sort().join('-');const notes=(card.querySelector('[data-product-notes]')?.value||'').trim();return `${card.dataset.id}:${opts}:utensils${card.querySelector('[data-utensils158]')?.checked?1:0}:notes${encodeURIComponent(notes)}`;}
  const personalized=()=>!!card.querySelector('.nu151-choose');
  function sync(){const quantity=window.NOWUP_CART160?.get(key())?.quantity||0;const blocked=!!card.querySelector('[data-add]')?.disabled;add.disabled=blocked;add.textContent=blocked?'Indisponível':'Adicionar';add.hidden=quantity>0&&!personalized();controls.hidden=!quantity||personalized();amount.value=String(quantity);amount.max=String(Number(card.dataset.max)||99);plus.disabled=blocked||quantity>=(Number(card.dataset.max)||99);minus.disabled=blocked;amount.disabled=blocked;}
  function increment(){const originalAdd=card.querySelector('[data-add]');if(!originalAdd||originalAdd.disabled)return;const choose=card.querySelector('.nu151-choose');if(choose){choose.click();return;}const originalQty=card.querySelector('[data-product-quantity]');if(originalQty)originalQty.value='1';originalAdd.click();sync();}
  // Reuse the cart's controls so quantities persist and totals update immediately.
  function decrement(){const control=Array.from(root.querySelectorAll('[data-minus]')).find(e=>e.dataset.minus===key());control?.click();sync();}
  function setQuantity(){const value=Math.max(0,Math.min(Number(card.dataset.max)||99,Math.trunc(Number(amount.value)||0)));if(!value){Array.from(root.querySelectorAll('[data-remove]')).find(e=>e.dataset.remove===key())?.click();sync();return;}const input=Array.from(root.querySelectorAll('[data-cart-quantity]')).find(e=>e.dataset.cartQuantity===key());if(input){input.value=String(value);input.dispatchEvent(new Event('input',{bubbles:true}));input.dispatchEvent(new Event('change',{bubbles:true}));}sync();}
  add.addEventListener('click',increment);plus.addEventListener('click',increment);minus.addEventListener('click',decrement);amount.addEventListener('input',()=>{if(amount.value!==''&&Number(amount.value)>0)setQuantity();});amount.addEventListener('change',setQuantity);
  content.append(add,controls);item.append(content);cartRefreshers.push(sync);sync();return item;
 }
 const buttons=nav?Array.from(nav.querySelectorAll('[data-category-filter]')):[],groups=new Map();
 buttons.filter(b=>b.dataset.categoryFilter!=='all').forEach(b=>groups.set(b.dataset.categoryFilter,{name:b.textContent.trim(),cards:[]}));
 originals.forEach(card=>{const key=card.dataset.category||'outros';if(!groups.has(key))groups.set(key,{name:card.querySelector('.menu-product-info small')?.textContent?.trim()||'Outros produtos',cards:[]});groups.get(key).cards.push(card);});
 groups.forEach((group,key)=>{
  if(!group.cards.length)return;
  const section=make('section','nu190-category');section.dataset.category190=key;sections.set(key,section);
  const header=make('header'),all=make('button','','Ver todos ›');all.type='button';all.addEventListener('click',()=>{showProducts();buttons.find(b=>b.dataset.categoryFilter===key)?.click();});header.append(make('h2','',group.name),all);section.append(header);
  const track=make('div','nu190-track');track.tabIndex=0;track.setAttribute('aria-label','Produtos de '+group.name+'; deslize para os lados');
  const pages=[];for(let i=0;i<group.cards.length;i+=4){const page=make('div','nu190-page');group.cards.slice(i,i+4).forEach(card=>page.append(compact(card)));pages.push(page);track.append(page);}section.append(track);
  const indicator=make('div','nu190-indicator'),prev=make('button','','‹'),next=make('button','','›'),dots=make('div','nu190-dots');prev.type=next.type='button';prev.setAttribute('aria-label','Página anterior de '+group.name);next.setAttribute('aria-label','Próxima página de '+group.name);
  let index=0;
  const dotButtons=pages.map((_,i)=>{const b=make('button');b.type='button';b.setAttribute('aria-label','Página '+(i+1)+' de '+group.name);b.addEventListener('click',()=>go(i));dots.append(b);return b;});
  function refresh(){index=Math.max(0,Math.min(pages.length-1,Math.round(track.scrollLeft/Math.max(track.clientWidth,1))));dotButtons.forEach((b,i)=>{b.classList.toggle('active',i===index);b.setAttribute('aria-current',i===index?'true':'false');});prev.disabled=index===0;next.disabled=index===pages.length-1;}
  function go(i){track.scrollTo({left:Math.max(0,Math.min(pages.length-1,i))*track.clientWidth,behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});}
  prev.addEventListener('click',()=>go(index-1));next.addEventListener('click',()=>go(index+1));track.addEventListener('scroll',refresh,{passive:true});
  track.addEventListener('keydown',event=>{if(event.target!==track)return;if(event.key==='ArrowRight'||event.key==='ArrowLeft'){event.preventDefault();go(index+(event.key==='ArrowRight'?1:-1));}});
  indicator.append(prev,dots,next);section.append(indicator,make('small','nu190-hint',pages.length>1?'Deslize para o lado':'Todos os produtos desta categoria'));refreshers.push(refresh);refresh();showcase.append(section);
 });
 if(!originals.length)showcase.append(make('p','nu190-empty','Esta loja ainda não publicou produtos.'));
 root.addEventListener('click',event=>{if(!body.classList.contains('nu187-store-home'))return;const button=event.target.closest('[data-category-filter]');if(!button)return;event.preventDefault();event.stopImmediatePropagation();(sections.get(button.dataset.categoryFilter)||showcase).scrollIntoView({block:'start',behavior:'auto'});},true);
 // Focus alone does not switch views: explicit top-search interaction does.
 search.addEventListener('click',()=>{if(body.classList.contains('nu187-store-home'))showProducts(true);});
 search.addEventListener('keydown',event=>{if(body.classList.contains('nu187-store-home')&&(event.key==='Enter'||event.key.length===1))showProducts();});
 search.addEventListener('input',()=>{if(body.classList.contains('nu187-store-home')&&search.value)showProducts();});
 back.addEventListener('click',()=>{if(body.classList.contains('nu187-store-home'))location.href='/';else showHome();});
 intro.querySelector('[data-store-promotion187]')?.addEventListener('click',()=>showProducts());
 window.addEventListener('nowup-cart-changed',()=>cartRefreshers.forEach(fn=>fn()));
 body.dataset.store187Ready='1';if(new URLSearchParams(location.search).has('produto')||/^#produto-/.test(location.hash))showProducts();else showHome();
});
