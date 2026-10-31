/* V190: compact category pages use the existing cart, product and option nodes. */
function catalogGroups275(cards){
 const combo=c=>c.dataset.combo256==='1'||(c.dataset.category||'').trim().toLowerCase()==='combos';
 return {regular:cards.filter(c=>!combo(c)),combos:cards.filter(c=>combo(c)&&c.dataset.available256==='1'),promotions:cards.filter(c=>Number(c.dataset.price)>0&&Number(c.dataset.price)<Number(c.dataset.regular256)&&c.dataset.available256==='1')};
}
if(typeof module!=='undefined')module.exports={catalogGroups275};
if(typeof document!=='undefined')document.addEventListener('DOMContentLoaded',()=>{
 'use strict';
 const body=document.body,root=document.querySelector('[data-native-menu]');
 const template=document.getElementById('nu187-store-template');
 const heading=root?.querySelector('.nu83-catalog-heading'),layout=root?.querySelector('.menu-layout');
 const search=heading?.querySelector('[data-product-search], [data-store-search]');
 if(!root||!template||!heading||!layout||!search){body.classList.remove('nu187-store-home');return;}
 const pageSize235=({large:1,pair:2})[root.dataset.carouselLayout]||4;
 const desktop228=matchMedia('(min-width:901px)');
 const desktopStyle228=document.createElement('style');
 desktopStyle228.textContent=`@media(min-width:901px){
 html body.public-profile-area.nu228-desktop-catalog [data-native-menu] .nu187-intro{display:block!important}
 html body.public-profile-area.nu228-desktop-catalog [data-native-menu] .nu207-banners{display:block!important;position:relative!important;top:auto!important;inset:auto!important;z-index:auto!important;box-shadow:none!important}
 html body.public-profile-area.nu228-desktop-catalog [data-native-menu] .nu-menu-sticky{position:sticky!important;top:0!important;z-index:100!important;background:#fff!important}
 }`;
 document.head.append(desktopStyle228);
 const cardsStyle229=document.createElement('style');cardsStyle229.textContent="\nhtml body.public-profile-area [data-native-menu] .nu190-showcase .nu190-page{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important;grid-template-rows:repeat(2,auto)!important;gap:12px!important;padding:0 2px!important;box-sizing:border-box}\nhtml body.public-profile-area [data-native-menu] .nu190-showcase .nu201-card{display:grid!important;grid-template-columns:minmax(48px,36%) minmax(0,1fr)!important;min-height:clamp(180px,27svh,240px)!important;height:auto!important;padding:12px 9px!important;gap:8px!important;border-radius:16px!important;align-items:center!important;box-sizing:border-box;min-width:0}\nhtml body.public-profile-area [data-native-menu] .nu190-showcase .nu201-card>img,html body.public-profile-area [data-native-menu] .nu190-showcase .nu201-card>.nu190-no-image{width:100%!important;height:clamp(125px,20svh,175px)!important;object-fit:contain!important}\nhtml body.public-profile-area [data-native-menu] .nu190-showcase .nu201-card h3{font-size:clamp(13px,3.6vw,17px)!important;line-height:1.25!important;margin:0 0 9px!important;-webkit-line-clamp:3!important;overflow-wrap:anywhere}\nhtml body.public-profile-area [data-native-menu] .nu190-showcase .nu201-card strong{font-size:clamp(17px,4.5vw,22px)!important;margin:0 0 10px!important;display:block}\nhtml body.public-profile-area [data-native-menu] .nu190-showcase .nu201-open{width:100%!important;min-height:42px!important;padding:8px 3px!important;font-size:12px!important;white-space:normal!important}\nhtml body.public-profile-area [data-native-menu] .nu190-showcase .nu201-card.nu201-selected{grid-template-columns:minmax(0,1fr)!important}\nhtml body.public-profile-area [data-native-menu] .nu190-showcase .nu190-category>header{display:flex!important;align-items:center!important;justify-content:space-between!important;gap:10px!important;margin:16px 0 12px!important}\nhtml body.public-profile-area [data-native-menu] .nu190-showcase .nu190-category>header h2{display:flex!important;align-items:center!important;gap:10px!important;font-size:clamp(23px,6vw,32px)!important;font-weight:800!important;color:#381267!important;line-height:1.15!important;margin:0!important;min-width:0;overflow-wrap:anywhere}\n.nu229-category-icon{display:inline-flex;align-items:center;justify-content:center;flex:0 0 44px;width:44px;height:44px;border-radius:50%;background:#7132bf;color:#fff;font-size:24px}\nhtml body.public-profile-area [data-native-menu] .nu190-showcase .nu190-category>header>button{flex:none;min-height:40px!important;font-size:12px!important;padding:8px!important;border-radius:12px!important}\n@media(max-width:350px){html body.public-profile-area [data-native-menu] .nu190-showcase .nu201-card{grid-template-columns:minmax(0,1fr)!important;min-height:255px!important}html body.public-profile-area [data-native-menu] .nu190-showcase .nu201-card>img{height:110px!important}}\n";document.head.append(cardsStyle229);
 const make=(tag,cls,text)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;};
 const intro=template.content.firstElementChild.cloneNode(true),nav=root.querySelector('.menu-category-nav');
 const sticky=root.querySelector('.nu-menu-sticky')||heading.parentElement;
 const anchor=document.createComment('store190');layout.before(anchor);anchor.before(intro);
 const showcase=make('div','nu190-showcase');layout.before(showcase);
 const originals=Array.from(layout.querySelectorAll('[data-product]')),sections=new Map(),refreshers=[],cartRefreshers=[];
 originals.forEach(card=>{if(card.dataset.combo256==='1'||card.dataset.category==='combos'){card.dataset.category='combos';const label=card.querySelector('.menu-product-info small');if(label)label.textContent='Combos';}});
 const back=make('button','nu187-back','←');back.type='button';heading.prepend(back);
 let homeScroll=0,selectedCategory=null;
 const categoryView=make('section','nu191-category-view');categoryView.hidden=true;layout.before(categoryView);
 const categoryTitle=make('h2'),categoryCount=make('p','nu191-count'),categoryEmpty=make('p','nu191-empty','Nenhum produto encontrado nesta categoria.');categoryEmpty.hidden=true;
 const categoryHeader=make('header','nu219-category-header'),less=make('button','nu219-less','Ver menos ⌃');
 less.type='button';less.setAttribute('aria-label','Recolher produtos e voltar aos carrosséis');
 categoryHeader.style.cssText='display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap';
 categoryTitle.style.margin='0';less.style.cssText='border:1px solid #e6dcf2;background:#f5effc;color:#7132bf;border-radius:10px;padding:10px 14px;min-height:44px;font:inherit;font-size:14px;font-weight:700;cursor:pointer';
 less.addEventListener('click',()=>{const key=selectedCategory;showHome();const section=sections.get(key);if(section){section.scrollIntoView({block:'start',behavior:'auto'});section.querySelector('header button')?.focus({preventScroll:true});}});
 categoryHeader.append(categoryTitle,less);categoryView.append(categoryHeader,categoryCount,categoryEmpty);const categoryCache=new Map();
 const money=cents=>(cents/100).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
 const resize=()=>window.dispatchEvent(new Event('resize'));
 function showProducts(focus=false){
  if(body.classList.contains('nu187-store-home'))homeScroll=window.scrollY;
  selectedCategory=null;categoryView.hidden=true;body.classList.remove('nu191-category');
  intro.hidden=!desktop228.matches;showcase.hidden=true;body.classList.toggle('nu228-desktop-catalog',desktop228.matches);back.setAttribute('aria-label','Voltar às informações da loja');
  if(nav)sticky.append(nav);body.classList.remove('nu187-store-home');search.placeholder='Buscar nesta loja';search.setAttribute('aria-label','Buscar produtos nesta loja');
  resize();window.scrollTo({top:0,behavior:'instant'});if(focus)search.focus({preventScroll:true});
 }
 function showHome(){
  body.classList.remove('nu228-desktop-catalog');

  selectedCategory=null;categoryView.hidden=true;body.classList.remove('nu191-category');
  intro.hidden=false;showcase.hidden=false;body.classList.add('nu187-store-home');back.setAttribute('aria-label','Voltar ao início do NowUp');
  if(nav)anchor.after(nav);search.value='';search.dispatchEvent(new Event('input',{bubbles:true}));search.placeholder='Pesquisar produtos';search.setAttribute('aria-label','Pesquisar produtos nesta loja');search.blur();
  refreshers.forEach(fn=>fn());cartRefreshers.forEach(fn=>fn());resize();window.scrollTo({top:homeScroll,behavior:'instant'});
 }
 function compact(card){
  const item=make('article','nu190-card nu201-card'),image=card.querySelector('.nu163-media img, img');
  if(image){const photo=make('img');photo.decoding='async';if(image.dataset.src258){photo.src='/static/product-placeholder.svg';photo.dataset.src258=image.dataset.src258;}else{photo.src=image.getAttribute('src')||image.currentSrc;}photo.alt='';photo.loading='lazy';photo.addEventListener('error',()=>{photo.src='/static/product-placeholder.svg';},{once:true});item.append(photo);}
  else item.append(make('div','nu190-no-image','🍽'));
  if(card.dataset.cold==='1'){const ice=make('span','nu201-ice','❄');ice.title='Vendido gelado';ice.setAttribute('aria-label','Vendido gelado');item.append(ice);}
  item.dataset.source256=card.dataset.id;item.classList.toggle('nu275-combo-card',card.dataset.combo256==='1'||card.dataset.category==='combos');
  const regular=Number(card.dataset.regular256),price=Number(card.dataset.price);
  item.classList.toggle('nu256-highlight',card.dataset.combo256==='1'||(price>0&&regular>price));
  if(regular>price){const badge=make('span','nu256-discount','🔥 -'+Math.round((regular-price)*100/regular)+'%');item.prepend(badge);}
  const content=make('div','nu190-card-content');content.append(make('h3','',card.dataset.name||'Produto'),make('strong','',money(Number(card.dataset.price)||0)));
  if(item.classList.contains('nu275-combo-card'))item.prepend(make('span','nu284-combo-badge','COMBO'));
  if(regular>price)content.insertBefore(make('del','nu284-old-price',money(regular)),content.querySelector('strong'));
  if(item.classList.contains('nu275-combo-card')){const priceBox=make('div','nu289-combo-price'),label=make('small','','Preço do combo'),old=content.querySelector('.nu284-old-price'),value=content.querySelector('strong');priceBox.append(label);if(old)priceBox.append(old);priceBox.append(value);content.append(priceBox);}
  const toggle=make('button','nu201-open','Adicionar');toggle.type='button';toggle.setAttribute('aria-label','Adicionar '+card.dataset.name);toggle.setAttribute('aria-expanded','false');
  const panel=make('div','nu201-panel');panel.hidden=true;
  const controls=make('div','nu190-amount'),minus=make('button','','−'),plus=make('button','','+'),amount=make('input');minus.type=plus.type='button';
  minus.setAttribute('aria-label','Diminuir quantidade');plus.setAttribute('aria-label','Aumentar quantidade');amount.type='number';amount.min='1';amount.max=String(Number(card.dataset.max)||99);amount.value='1';amount.step='1';amount.inputMode='numeric';amount.setAttribute('aria-label','Quantidade de '+card.dataset.name);controls.append(minus,amount,plus);
  const add=make('button','nu190-add','Adicionar');add.type='button';const back=make('button','nu201-back','Voltar');back.type='button';
  function normalize(){const n=Math.max(1,Math.min(Number(amount.max),Math.trunc(Number(amount.value)||1)));amount.value=String(n);minus.disabled=n<=1;plus.disabled=n>=Number(amount.max);return n;}
  function close(){panel.hidden=true;toggle.hidden=(window.NOWUP_CART160?.quantity(card.dataset.id)||0)>0;toggle.setAttribute('aria-expanded','false');item.classList.remove('nu201-selected');}
  const chosen=make('small','nu-cart-selected262');chosen.hidden=true;chosen.setAttribute('aria-live','polite');content.append(chosen);const step=make('div','nu-step263'),less=make('button','','−'),number=make('span'),more=make('button','','+');less.type=more.type='button';less.setAttribute('aria-label','Remover uma unidade de '+card.dataset.name);more.setAttribute('aria-label','Adicionar uma unidade de '+card.dataset.name);number.setAttribute('aria-live','polite');step.append(less,number,more);step.hidden=true;less.onclick=()=>window.NOWUP_CART160?.adjust(card.dataset.id,-1);more.onclick=()=>window.NOWUP_CART160?.adjust(card.dataset.id,1);
  function sync(){const count=window.NOWUP_CART160?.quantity(card.dataset.id)||0;chosen.hidden=true;step.hidden=count===0;toggle.hidden=count>0||!panel.hidden;number.textContent=String(count);if(count>0){panel.hidden=true;item.classList.remove('nu201-selected');}more.disabled=!!card.querySelector('[data-add]')?.disabled||count>=Number(card.dataset.max||99);item.classList.toggle('nu-cart-in262',count>0);const blocked=!!card.querySelector('[data-add]')?.disabled;toggle.disabled=blocked;add.disabled=blocked;toggle.textContent=blocked?'Indisponível':item.classList.contains('nu275-combo-card')?'›':'Adicionar';if(item.classList.contains('nu275-combo-card')){toggle.hidden=false;step.hidden=true;}normalize();}
  function open(){if(toggle.disabled)return;if(item.classList.contains('nu275-combo-card')){card.querySelector('.nu151-choose')?.click();return;}panel.hidden=false;toggle.hidden=true;toggle.setAttribute('aria-expanded','true');item.classList.add('nu201-selected');normalize();}
  toggle.addEventListener('click',open);item.addEventListener('click',e=>{if(!e.target.closest('button,input,a,label')&&panel.hidden&&(item.classList.contains('nu275-combo-card')||!(window.NOWUP_CART160?.quantity(card.dataset.id)||0)))open();});
  minus.addEventListener('click',()=>{amount.value=String(normalize()-1);normalize();});plus.addEventListener('click',()=>{amount.value=String(normalize()+1);normalize();});amount.addEventListener('change',normalize);
  add.addEventListener('click',()=>{const original=card.querySelector('[data-add]');if(!original||original.disabled)return;const choose=card.querySelector('.nu151-choose');if(choose){choose.click();return;}const quantity=card.querySelector('[data-product-quantity]');if(quantity)quantity.value=String(normalize());original.click();close();});back.addEventListener('click',()=>{close();toggle.focus();});
  panel.append(controls,add,back);const actions=make('div','nu-cart-actions262');actions.append(toggle,step);if(item.classList.contains('nu275-combo-card')){toggle.classList.add('nu284-combo-open');toggle.setAttribute('aria-label','Personalizar '+card.dataset.name);step.hidden=true;}content.append(actions,panel);item.append(content);cartRefreshers.push(sync);sync();return item;
 }
 const buttons=nav?Array.from(nav.querySelectorAll('[data-category-filter]')):[],groups=new Map();
 buttons.filter(b=>b.dataset.categoryFilter!=='all').forEach(b=>groups.set(b.dataset.categoryFilter,{name:b.textContent.trim(),cards:[]}));
 const catalog275=catalogGroups275(originals);
 catalog275.regular.forEach(card=>{const key=card.dataset.category||'outros';if(!groups.has(key))groups.set(key,{name:card.querySelector('.menu-product-info small')?.textContent?.trim()||'Outros produtos',cards:[]});groups.get(key).cards.push(card);});
 const offers256=catalog275.promotions;
 const combos256=catalog275.combos;
 groups.forEach((group,key)=>{if(!group.cards.length){groups.delete(key);const b=buttons.find(b=>b.dataset.categoryFilter===key);b?.remove();}});
 const special256=new Map();
 if(combos256.length)special256.set('__combos256',{name:'Combos',cards:combos256});
 if(offers256.length)special256.set('__offers256',{name:'Promoções',cards:offers256});
 const ordered256=new Map([...special256,...groups]);
 special256.forEach((value,key)=>groups.set(key,value));
 const categoryBar274=nav||make('nav','menu-category-nav');
 if(!nav)sticky.append(categoryBar274);
 const firstCategory274=categoryBar274.querySelector('[data-category-filter]:not([data-category-filter="all"])');
 special256.forEach((group,key)=>{const b=make('button','',key==='__offers256'?'Promoções':'Combos');b.type='button';b.dataset.categoryFilter=key;b.replaceChildren(window.NowUpCategory230.create(group.name),make('span','nu230-label',group.name));b.addEventListener('click',()=>showCategory(key));categoryBar274.insertBefore(b,firstCategory274);buttons.push(b);});
 categoryBar274.classList.add('nu274-categories');
 const normalize274=text=>text.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
 const palettes274=[['#6410c9','#8c16ef'],['#197638','#258b45'],['#b7111c','#df2430']];
 buttons.forEach((b,index)=>{const key=b.dataset.categoryFilter,text=normalize274(b.textContent);let colors=palettes274[index%palettes274.length];
 if(key==='all'||key==='__combos256')colors=palettes274[0];
 else if(key==='__offers256')colors=palettes274[2];
 else if(/cerveja|chopp/.test(text))colors=palettes274[1];
 else if(/destilado|whisk|vodka/.test(text))colors=palettes274[0];
 else if(/refrigerante|suco/.test(text))colors=['#b7111c','#e12830'];
 else if(/gelo|carvao|agua/.test(text))colors=palettes274[1];
 b.style.setProperty('--nu274-start',colors[0]);b.style.setProperty('--nu274-end',colors[1]);});
 ordered256.forEach((group,key)=>{
  if(!group.cards.length)return;
  const section=make('section','nu190-category');section.dataset.category190=key;section.classList.toggle('nu275-combo-section',key==='__combos256');sections.set(key,section);
  const header=make('header'),all=make('button','','Ver todos ›');all.type='button';all.addEventListener('click',()=>showCategory(key));const title=make('h2','nu286-category-label'),icon=make('span','nu284-category-icon');icon.setAttribute('aria-hidden','true');icon.replaceChildren(window.NowUpCategory230.create(group.name));title.append(icon,document.createTextNode(group.name));header.append(title,all);section.append(header);
  const track=make('div','nu190-track');track.tabIndex=0;track.setAttribute('aria-label','Produtos de '+group.name+'; deslize para os lados');
  const pages=[],pageSources238=[];
  const pageSize275=key==='__combos256'?1:pageSize235;
  for(let i=0;i<group.cards.length;i+=pageSize275){const page=make('div','nu190-page');page.style.minHeight='150px';pageSources238.push(group.cards.slice(i,i+pageSize275));pages.push(page);track.append(page);}
  function loadPage238(i){const page=pages[i];if(!page||page.dataset.loaded238)return;page.dataset.loaded238='1';pageSources238[i].forEach(card=>page.append(compact(card)));}
  loadPage238(0);loadPage238(1);section.append(track);
  const indicator=make('div','nu190-indicator'),prev=make('button','','‹'),next=make('button','','›'),dots=make('div','nu190-dots');prev.type=next.type='button';prev.setAttribute('aria-label','Página anterior de '+group.name);next.setAttribute('aria-label','Próxima página de '+group.name);
  let index=0;
  const dotButtons=pages.map((_,i)=>{const b=make('button');b.type='button';b.setAttribute('aria-label','Página '+(i+1)+' de '+group.name);b.addEventListener('click',()=>go(i));dots.append(b);return b;});
  function refresh(){index=pages.reduce((best,page,i)=>Math.abs(track.scrollLeft-(page.offsetLeft-pages[0].offsetLeft))<Math.abs(track.scrollLeft-(pages[best].offsetLeft-pages[0].offsetLeft))?i:best,0);loadPage238(index);loadPage238(index+1);dotButtons.forEach((b,i)=>{b.classList.toggle('active',i===index);b.setAttribute('aria-current',i===index?'true':'false');});prev.disabled=index===0;next.disabled=index===pages.length-1;}
  function go(i){loadPage238(i);loadPage238(i+1);track.scrollTo({left:pages[Math.max(0,Math.min(pages.length-1,i))].offsetLeft-pages[0].offsetLeft,behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});}
  prev.addEventListener('click',()=>go(index-1));next.addEventListener('click',()=>go(index+1));track.addEventListener('scroll',refresh,{passive:true});
  track.addEventListener('keydown',event=>{if(event.target!==track)return;if(event.key==='ArrowRight'||event.key==='ArrowLeft'){event.preventDefault();go(index+(event.key==='ArrowRight'?1:-1));}});
  indicator.append(prev,dots,next);section.append(indicator,make('small','nu190-hint',pages.length>1?'Deslize para o lado':'Todos os produtos desta categoria'));refreshers.push(refresh);refresh();showcase.append(section);
 });
 function filterCategory(){
  if(!selectedCategory)return;
  const entry=categoryCache.get(selectedCategory),query=search.value.trim();let count=0;
  entry.cards.forEach(({source,node})=>{const text=(source.dataset.name||'')+' '+(source.querySelector('.menu-product-info p')?.textContent||'');const match=window.NowUpSearch179?window.NowUpSearch179.matches(text,query):text.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().includes(query.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase());node.hidden=!match;if(match)count++;});
  categoryCount.textContent=count+' '+(count===1?'produto':'produtos');categoryEmpty.hidden=count>0;
 }
 function showCategory(key){
  const group=groups.get(key);if(!group)return;
  if(body.classList.contains('nu187-store-home'))homeScroll=window.scrollY;
  selectedCategory=key;buttons.forEach(b=>{const active=b.dataset.categoryFilter===key;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active));});body.classList.remove('nu187-store-home');body.classList.add('nu191-category');
  intro.hidden=true;showcase.hidden=true;categoryView.hidden=false;back.setAttribute('aria-label','Voltar à página da loja');
  if(nav)sticky.append(nav);
  if(!categoryCache.has(key)){
   const grid=make('div','nu191-grid');grid.classList.toggle('nu275-combos-grid',key==='__combos256'||key==='__offers256');grid.classList.toggle('nu277-promotions-grid',key==='__offers256');const cards=group.cards.map(source=>{const node=compact(source);grid.append(node);return {source,node};});categoryView.append(grid);categoryCache.set(key,{grid,cards});
  }
  categoryCache.forEach((entry,k)=>entry.grid.hidden=k!==key);
  categoryView.classList.toggle('nu276-combo-view',key==='__combos256'||key==='__offers256');
  const viewName276=key==='__combos256'?'Combos':key==='__offers256'?'Promoções':group.name;
  categoryTitle.replaceChildren(window.NowUpCategory230.create(viewName276),document.createTextNode(viewName276));search.value='';search.placeholder=key==='__combos256'?'Buscar combos':key==='__offers256'?'Buscar promoções':'Buscar em '+group.name;search.setAttribute('aria-label',search.placeholder);filterCategory();
  resize();window.scrollTo({top:0,behavior:'instant'});requestAnimationFrame(sizeCombos275);
 }
 function sizeCombos275(){const grid=categoryCache.get(selectedCategory)?.grid;if(!['__combos256','__offers256'].includes(selectedCategory)||!grid)return;const top=Math.max(grid.getBoundingClientRect().top,sticky.getBoundingClientRect().bottom+70),dock=root.querySelector('.nu83-cart-dock:not([hidden])'),bottom=dock?dock.getBoundingClientRect().height+18:20;grid.style.setProperty('--nu275-grid-card-height',Math.max(280,Math.min(520,Math.floor(window.innerHeight-top-bottom-10)))+'px');}
 window.addEventListener('resize',()=>requestAnimationFrame(sizeCombos275));
 root.addEventListener('input',event=>{if(event.target===search&&selectedCategory){event.stopImmediatePropagation();filterCategory();}},true);
 root.addEventListener('search',event=>{if(event.target===search&&selectedCategory){event.stopImmediatePropagation();filterCategory();}},true);
 if(!originals.length)showcase.append(make('p','nu190-empty','Esta loja ainda não publicou produtos.'));
 root.addEventListener('click',event=>{if(!body.classList.contains('nu187-store-home')&&!selectedCategory)return;const button=event.target.closest('[data-category-filter]');if(!button)return;event.preventDefault();event.stopImmediatePropagation();buttons.forEach(b=>{const active=b===button;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active));});if(selectedCategory){if(button.dataset.categoryFilter==='all')showHome();else showCategory(button.dataset.categoryFilter);return;}(sections.get(button.dataset.categoryFilter)||showcase).scrollIntoView({block:'start',behavior:'auto'});},true);
 // Focus alone does not switch views: explicit top-search interaction does.
 search.addEventListener('click',()=>{if(body.classList.contains('nu187-store-home'))showProducts(true);});
 search.addEventListener('keydown',event=>{if(body.classList.contains('nu187-store-home')&&(event.key==='Enter'||event.key.length===1))showProducts();});
 search.addEventListener('input',()=>{if(body.classList.contains('nu187-store-home')&&search.value)showProducts();});
 back.addEventListener('click',()=>{if(desktop228.matches||body.classList.contains('nu187-store-home'))location.href='/';else showHome();});
 intro.querySelector('[data-store-promotion187]')?.addEventListener('click',()=>showCategory('__offers256'));
 function syncNative262(){originals.forEach(card=>{const button=card.querySelector('[data-add]');if(!button)return;let step=card.querySelector('[data-step263]');if(!step){step=make('div','nu-step263');step.dataset.step263='';const less=make('button','','−'),number=make('span'),more=make('button','','+');less.type=more.type='button';less.setAttribute('aria-label','Remover uma unidade de '+card.dataset.name);more.setAttribute('aria-label','Adicionar uma unidade de '+card.dataset.name);number.setAttribute('aria-live','polite');less.onclick=()=>window.NOWUP_CART160?.adjust(card.dataset.id,-1);more.onclick=()=>window.NOWUP_CART160?.adjust(card.dataset.id,1);step.append(less,number,more);button.after(step);}const count=window.NOWUP_CART160?.quantity(card.dataset.id)||0;step.hidden=count===0;step.querySelector('span').textContent=String(count);step.lastElementChild.disabled=button.disabled||count>=Number(card.dataset.max||99);button.hidden=count>0;card.classList.toggle('nu-cart-in262',count>0);});}
 syncNative262();window.addEventListener('nowup-cart-changed',()=>{cartRefreshers.forEach(fn=>fn());syncNative262();});
 desktop228.addEventListener('change',()=>showHome());
 body.dataset.store187Ready='1';if(new URLSearchParams(location.search).has('produto')||/^#produto-/.test(location.hash))showProducts();else showHome();
});
