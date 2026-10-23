/* V190: compact category pages use the existing cart, product and option nodes. */
document.addEventListener('DOMContentLoaded',()=>{
 'use strict';
 const body=document.body,root=document.querySelector('[data-native-menu]');
 const template=document.getElementById('nu187-store-template');
 const heading=root?.querySelector('.nu83-catalog-heading'),layout=root?.querySelector('.menu-layout');
 const search=heading?.querySelector('[data-product-search], [data-store-search]');
 if(!root||!template||!heading||!layout||!search){body.classList.remove('nu187-store-home');return;}
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
 // Category selector occupies its container, never viewport plus sidebar.
 if(nav)nav.classList.add('categories-wrapper');
 const sticky=root.querySelector('.nu-menu-sticky')||heading.parentElement;
 const anchor=document.createComment('store190');layout.before(anchor);anchor.before(intro);
 const showcase=make('div','nu190-showcase');layout.before(showcase);
 const originals=Array.from(layout.querySelectorAll('[data-product]')),sections=new Map(),refreshers=[],cartRefreshers=[];
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
  if(desktop228.matches){showProducts();return;}
  selectedCategory=null;categoryView.hidden=true;body.classList.remove('nu191-category');
  intro.hidden=false;showcase.hidden=false;body.classList.add('nu187-store-home');back.setAttribute('aria-label','Voltar ao início do NowUp');
  if(nav)anchor.after(nav);search.value='';search.dispatchEvent(new Event('input',{bubbles:true}));search.placeholder='Pesquisar produtos';search.setAttribute('aria-label','Pesquisar produtos nesta loja');search.blur();
  refreshers.forEach(fn=>fn());cartRefreshers.forEach(fn=>fn());resize();window.scrollTo({top:homeScroll,behavior:'instant'});
 }
 function compact(card){
  const item=make('article','nu190-card nu201-card'),image=card.querySelector('.nu163-media img, img');
  if(image){const photo=make('img');photo.src=image.currentSrc||image.getAttribute('src');photo.alt='';photo.loading='lazy';photo.addEventListener('error',()=>{photo.src='/static/product-placeholder.svg';},{once:true});item.append(photo);}
  else item.append(make('div','nu190-no-image','🍽'));
  if(card.dataset.cold==='1'){const ice=make('span','nu201-ice','❄');ice.title='Vendido gelado';ice.setAttribute('aria-label','Vendido gelado');item.append(ice);}
  const content=make('div','nu190-card-content');content.append(make('h3','',card.dataset.name||'Produto'),make('strong','',money(Number(card.dataset.price)||0)));
  const toggle=make('button','nu201-open','Escolher');toggle.type='button';toggle.setAttribute('aria-label','Escolher '+card.dataset.name);toggle.setAttribute('aria-expanded','false');
  const panel=make('div','nu201-panel');panel.hidden=true;
  const controls=make('div','nu190-amount'),minus=make('button','','−'),plus=make('button','','+'),amount=make('input');minus.type=plus.type='button';
  minus.setAttribute('aria-label','Diminuir quantidade');plus.setAttribute('aria-label','Aumentar quantidade');amount.type='number';amount.min='1';amount.max=String(Number(card.dataset.max)||99);amount.value='1';amount.step='1';amount.inputMode='numeric';amount.setAttribute('aria-label','Quantidade de '+card.dataset.name);controls.append(minus,amount,plus);
  const add=make('button','nu190-add','Adicionar');add.type='button';const back=make('button','nu201-back','Voltar');back.type='button';
  function normalize(){const n=Math.max(1,Math.min(Number(amount.max),Math.trunc(Number(amount.value)||1)));amount.value=String(n);minus.disabled=n<=1;plus.disabled=n>=Number(amount.max);return n;}
  function close(){panel.hidden=true;toggle.hidden=false;toggle.setAttribute('aria-expanded','false');item.classList.remove('nu201-selected');}
  function sync(){const blocked=!!card.querySelector('[data-add]')?.disabled;toggle.disabled=blocked;add.disabled=blocked;toggle.textContent=blocked?'Indisponível':'Escolher';normalize();}
  function open(){if(toggle.disabled)return;panel.hidden=false;toggle.hidden=true;toggle.setAttribute('aria-expanded','true');item.classList.add('nu201-selected');normalize();}
  toggle.addEventListener('click',open);item.addEventListener('click',e=>{if(!e.target.closest('button,input,a,label')&&panel.hidden)open();});
  minus.addEventListener('click',()=>{amount.value=String(normalize()-1);normalize();});plus.addEventListener('click',()=>{amount.value=String(normalize()+1);normalize();});amount.addEventListener('change',normalize);
  add.addEventListener('click',()=>{const original=card.querySelector('[data-add]');if(!original||original.disabled)return;const choose=card.querySelector('.nu151-choose');if(choose){choose.click();return;}const quantity=card.querySelector('[data-product-quantity]');if(quantity)quantity.value=String(normalize());original.click();close();});back.addEventListener('click',()=>{close();toggle.focus();});
  panel.append(controls,add,back);content.append(toggle,panel);item.append(content);cartRefreshers.push(sync);sync();return item;
 }
 const buttons=nav?Array.from(nav.querySelectorAll('[data-category-filter]')):[],groups=new Map();
 buttons.filter(b=>b.dataset.categoryFilter!=='all').forEach(b=>groups.set(b.dataset.categoryFilter,{name:b.textContent.trim(),cards:[]}));
 originals.forEach(card=>{const key=card.dataset.category||'outros';if(!groups.has(key))groups.set(key,{name:card.querySelector('.menu-product-info small')?.textContent?.trim()||'Outros produtos',cards:[]});groups.get(key).cards.push(card);});
 groups.forEach((group,key)=>{
  if(!group.cards.length)return;
  const section=make('section','nu190-category');section.dataset.category190=key;sections.set(key,section);
  const header=make('header'),all=make('button','','Ver todos ›');all.type='button';all.addEventListener('click',()=>showCategory(key));const title=make('h2'),icon=make('span','nu229-category-icon');icon.setAttribute('aria-hidden','true');const name=group.name.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();icon.textContent=/cerveja|chopp/.test(name)?'🍺':/refrigerante|suco|bebida/.test(name)?'🥤':/agua/.test(name)?'💧':/lanche|burger/.test(name)?'🍔':/pizza/.test(name)?'🍕':/doce|chocolate/.test(name)?'🍫':/vinho/.test(name)?'🍷':/gelad|gelo/.test(name)?'❄':'▦';title.append(icon,document.createTextNode(group.name));header.append(title,all);section.append(header);
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
 function filterCategory(){
  if(!selectedCategory)return;
  const entry=categoryCache.get(selectedCategory),query=search.value.trim();let count=0;
  entry.cards.forEach(({source,node})=>{const text=(source.dataset.name||'')+' '+(source.querySelector('.menu-product-info p')?.textContent||'');const match=window.NowUpSearch179?window.NowUpSearch179.matches(text,query):text.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().includes(query.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase());node.hidden=!match;if(match)count++;});
  categoryCount.textContent=count+' '+(count===1?'produto':'produtos');categoryEmpty.hidden=count>0;
 }
 function showCategory(key){
  const group=groups.get(key);if(!group)return;
  if(body.classList.contains('nu187-store-home'))homeScroll=window.scrollY;
  selectedCategory=key;body.classList.remove('nu187-store-home');body.classList.add('nu191-category');
  intro.hidden=true;showcase.hidden=true;categoryView.hidden=false;back.setAttribute('aria-label','Voltar à página da loja');
  if(nav)sticky.append(nav);
  if(!categoryCache.has(key)){
   const grid=make('div','nu191-grid'),cards=group.cards.map(source=>{const node=compact(source);grid.append(node);return {source,node};});categoryView.append(grid);categoryCache.set(key,{grid,cards});
  }
  categoryCache.forEach((entry,k)=>entry.grid.hidden=k!==key);
  categoryTitle.textContent=group.name;search.value='';search.placeholder='Buscar em '+group.name;search.setAttribute('aria-label','Buscar em '+group.name);filterCategory();
  resize();window.scrollTo({top:0,behavior:'instant'});
 }
 root.addEventListener('input',event=>{if(event.target===search&&selectedCategory){event.stopImmediatePropagation();filterCategory();}},true);
 root.addEventListener('search',event=>{if(event.target===search&&selectedCategory){event.stopImmediatePropagation();filterCategory();}},true);
 if(!originals.length)showcase.append(make('p','nu190-empty','Esta loja ainda não publicou produtos.'));
 root.addEventListener('click',event=>{if(!body.classList.contains('nu187-store-home')&&!selectedCategory)return;const button=event.target.closest('[data-category-filter]');if(!button)return;event.preventDefault();event.stopImmediatePropagation();if(selectedCategory){if(button.dataset.categoryFilter==='all')showHome();else showCategory(button.dataset.categoryFilter);return;}(sections.get(button.dataset.categoryFilter)||showcase).scrollIntoView({block:'start',behavior:'auto'});},true);
 // Focus alone does not switch views: explicit top-search interaction does.
 search.addEventListener('click',()=>{if(body.classList.contains('nu187-store-home'))showProducts(true);});
 search.addEventListener('keydown',event=>{if(body.classList.contains('nu187-store-home')&&(event.key==='Enter'||event.key.length===1))showProducts();});
 search.addEventListener('input',()=>{if(body.classList.contains('nu187-store-home')&&search.value)showProducts();});
 back.addEventListener('click',()=>{if(desktop228.matches||body.classList.contains('nu187-store-home'))location.href='/';else showHome();});
 intro.querySelector('[data-store-promotion187]')?.addEventListener('click',()=>showProducts());
 window.addEventListener('nowup-cart-changed',()=>cartRefreshers.forEach(fn=>fn()));
 desktop228.addEventListener('change',()=>{if(desktop228.matches)showProducts();else showHome();});
 body.dataset.store187Ready='1';if(new URLSearchParams(location.search).has('produto')||/^#produto-/.test(location.hash))showProducts();else showHome();
});
