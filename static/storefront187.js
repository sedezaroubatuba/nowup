/* V190: compact category pages use the existing cart, product and option nodes. */
function catalogGroups275(cards){
 const combo=c=>c.dataset.comboLocal303!=='1'&&(c.dataset.combo256==='1'||(c.dataset.combo256===undefined&&(c.dataset.category||'').trim().toLowerCase()==='combos'));
 return {regular:cards.filter(c=>!combo(c)),combos:cards.filter(c=>combo(c)&&c.dataset.available256==='1'),promotions:cards.filter(c=>Number(c.dataset.price)>0&&Number(c.dataset.price)<Number(c.dataset.regular256)&&c.dataset.available256==='1')};
}
function catalogExpansion347({grid,more,collapseButton,load,count,limit,refresh,section}){
 let expanded=false;
 function expand(){if(expanded)return;expanded=true;more.remove();load(count);Array.from(grid.children).forEach(card=>card.hidden=false);collapseButton.hidden=false;collapseButton.setAttribute('aria-expanded','true');more.setAttribute('aria-expanded','true');refresh();}
 function collapse(){expanded=false;Array.from(grid.children).forEach((card,index)=>card.hidden=index>=limit);grid.append(more);more.hidden=false;more.setAttribute('aria-expanded','false');collapseButton.hidden=true;collapseButton.setAttribute('aria-expanded','false');section.scrollIntoView({block:'start',behavior:'auto'});more.focus({preventScroll:true});}
 return {expand,collapse};
}
if(typeof module!=='undefined')module.exports={catalogGroups275,catalogExpansion347};
if(typeof document!=='undefined')document.addEventListener('DOMContentLoaded',()=>{
 'use strict';
 const body=document.body,root=document.querySelector('[data-native-menu]');
 const template=document.getElementById('nu187-store-template');
 const heading=root?.querySelector('.nu83-catalog-heading'),layout=root?.querySelector('.menu-layout');
 const search=heading?.querySelector('[data-product-search], [data-store-search]');
 if(!root||!template||!heading||!layout||!search){body.classList.remove('nu187-store-home');return;}
 const pageSize235=({large:1,pair:2,three:3,six:6,eight:8})[root.dataset.carouselLayout]||4;
 const desktop228=matchMedia('(min-width:901px)');
 if(desktop228.matches)root.id='nu312-catalog';
 const desktopSheet312=document.createElement('link');desktopSheet312.rel='stylesheet';desktopSheet312.href='/static/catalog-desktop312.css?v=466';document.head.append(desktopSheet312);
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
 const catalogItems=layout.querySelector('.menu-products')||layout;const originals=Array.from(catalogItems.children).filter(el=>el.matches('[data-product]')),sections=new Map(),refreshers=[],cartRefreshers=[];
 originals.forEach(card=>{if(card.dataset.comboLocal303!=='1'&&(card.dataset.combo256==='1'||card.dataset.category==='combos')){card.dataset.category='combos';const label=card.querySelector('.menu-product-info small');if(label)label.textContent='Combos';}});
 const back=make('button','nu187-back','←');back.type='button';heading.prepend(back);
 let homeScroll=0,selectedCategory=null,selectedSubcategory261='';
  const subcats261=[...root.querySelectorAll('[data-scid261]')].map(element=>({
    id:element.dataset.scid261,parent:element.dataset.parent261,name:element.dataset.name261
  }));
  const hasSubcategories261=key=>subcats261.some(sc=>sc.parent===key);
 const categoryView=make('section','nu191-category-view');categoryView.hidden=true;layout.before(categoryView);
 const categoryTitle=make('h2'),categoryCount=make('p','nu191-count'),categoryEmpty=make('p','nu191-empty','Nenhum produto encontrado nesta categoria.');categoryEmpty.hidden=true;
 const categoryHeader=make('header','nu219-category-header'),less=make('button','nu219-less','Ver menos ⌃');
 less.type='button';less.setAttribute('aria-label','Recolher produtos e voltar aos carrosséis');
 categoryHeader.style.cssText='display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap';
 categoryTitle.style.margin='0';less.style.cssText='border:1px solid #e6dcf2;background:#f5effc;color:#7132bf;border-radius:10px;padding:10px 14px;min-height:44px;font:inherit;font-size:14px;font-weight:700;cursor:pointer';
 function collapseCategory(){const key=selectedCategory;showHome();const section=sections.get(key);if(section){section.scrollIntoView({block:'start',behavior:'auto'});section.querySelector('header button')?.focus({preventScroll:true});}}
 less.addEventListener('click',collapseCategory);
 categoryHeader.append(less,categoryTitle);
 const categoryFooter=make('div','nu462-collapse-footer');
 const lessBottom=less.cloneNode(true);
 lessBottom.addEventListener('click',collapseCategory);
 categoryFooter.append(lessBottom);
 const subcategoryFilters=make('div','nu261-pills nu465-subcategories');
 subcategoryFilters.setAttribute('role','group');
 subcategoryFilters.setAttribute('aria-label','Subcategorias');
 categoryView.append(categoryHeader,categoryCount,categoryEmpty,categoryFooter);
 const categoryCache=new Map();
 function prepareSubcategories(key){
  selectedSubcategory261='';
  const choices=subcats261.filter(sc=>sc.parent===key);
  subcategoryFilters.hidden=!choices.length;
  const controls=[{id:'',name:'Todos da categoria'},...choices].map(({id,name})=>{
   const button=make('button','',name);
   button.type='button';
   button.setAttribute('aria-pressed',String(!id));
   button.addEventListener('click',()=>{
    if(selectedSubcategory261===id)return;
    controls.find(control=>control.getAttribute('aria-pressed')==='true')?.setAttribute('aria-pressed','false');
    selectedSubcategory261=id;
    button.setAttribute('aria-pressed','true');
    filterCategory();
    // Start the newly filtered list just below the pinned shopping controls.
    const inset=Math.max(0,parseFloat(getComputedStyle(sticky).top)||0);
    const target=window.scrollY+categoryView.getBoundingClientRect().top-sticky.getBoundingClientRect().height-inset-8;
    window.scrollTo({top:Math.max(0,target),behavior:'instant'});
   });
   return button;
  });
  subcategoryFilters.replaceChildren(...controls);
 }
 const money=cents=>(cents/100).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
 const resize=()=>window.dispatchEvent(new Event('resize'));
 function showProducts(focus=false){
  if(body.classList.contains('nu187-store-home'))homeScroll=window.scrollY;
  selectedCategory=null;subcategoryFilters.remove();activeCategory.hidden=true;categoryView.hidden=true;body.classList.remove('nu191-category');
  intro.hidden=!desktop228.matches;showcase.hidden=true;body.classList.toggle('nu228-desktop-catalog',desktop228.matches);back.setAttribute('aria-label','Voltar às informações da loja');
  if(nav)sticky.append(nav);body.classList.remove('nu187-store-home');search.placeholder='Buscar nesta loja';search.setAttribute('aria-label','Buscar produtos nesta loja');
  resize();window.scrollTo({top:0,behavior:'instant'});if(focus)search.focus({preventScroll:true});
 }
 function showHome(){
  body.classList.remove('nu228-desktop-catalog');

  selectedCategory=null;subcategoryFilters.remove();activeCategory.hidden=true;categoryView.hidden=true;body.classList.remove('nu191-category');
  intro.hidden=false;showcase.hidden=false;body.classList.add('nu187-store-home');back.setAttribute('aria-label','Voltar ao início do NowUp');
  if(nav)anchor.after(nav);search.value='';search.dispatchEvent(new Event('input',{bubbles:true}));search.placeholder='Pesquisar produtos';search.setAttribute('aria-label','Pesquisar produtos nesta loja');search.blur();
  refreshers.forEach(fn=>fn());cartRefreshers.forEach(fn=>fn());resize();window.scrollTo({top:homeScroll,behavior:'instant'});
 }
 function highlightRegularPrice(content){
  const price=content.querySelector('strong');
  const box=make('div','nu451-regular-price');
  price.replaceWith(box);
  box.append(price);
 }
 function compact(card,offer=false){
  // A cover represents several real products; never add one automatically.
  if(card.dataset.group260==='1'){
    const panel=make('article','nu190-card nu201-card nu260-showcase');
    const image=card.querySelector('.nu-group260-cover img');
    if(image){const photo=make('img');photo.src=image.getAttribute('src')||image.currentSrc;photo.alt='';photo.loading='lazy';panel.append(photo);}
    else panel.append(make('div','nu190-no-image','▦'));
    const content=make('div','nu190-card-content');
    content.append(make('h3','',card.dataset.name||'Produto'),make('strong','', 'A partir de '+money(Number(card.dataset.price)||0)));
    if(!offer)highlightRegularPrice(content);
    content.append(make('small','nu260-variant-count',card.querySelectorAll('.nu-group260-row').length+' sabores ou opções'));
    const choose=make('button','nu201-open','Escolher sabor');choose.type='button';
    choose.setAttribute('aria-label','Escolher variação de '+(card.dataset.name||'Produto'));
    choose.addEventListener('click',()=>{
      showProducts(false);
      card.open=true;
      requestAnimationFrame(()=>card.scrollIntoView({block:'center',behavior:'smooth'}));
    });
    content.append(choose);panel.append(content);
    panel.addEventListener('click',event=>{if(!event.target.closest('button,a,input'))choose.click();});
    return panel;
  }
  const item=make('article','nu190-card nu201-card'),image=card.querySelector('.nu163-media img, img');
  if(image){const photo=make('img');photo.decoding='async';if(image.dataset.src258){photo.src='/static/product-placeholder.svg';photo.dataset.src258=image.dataset.src258;}else{photo.src=image.getAttribute('src')||image.currentSrc;}photo.alt='';photo.loading='lazy';photo.addEventListener('error',()=>{photo.src='/static/product-placeholder.svg';},{once:true});item.append(photo);}
  else item.append(make('div','nu190-no-image','🍽'));
  if(card.dataset.cold==='1'){const ice=make('span','nu201-ice','❄');ice.title='Vendido gelado';ice.setAttribute('aria-label','Vendido gelado');item.append(ice);}
  item.classList.toggle('nu293-offer-card',offer);item.dataset.source256=card.dataset.id;item.classList.toggle('nu275-combo-card',card.dataset.combo256==='1'||(card.dataset.combo256===undefined&&card.dataset.category==='combos'));
  const regular=Number(card.dataset.regular256),price=Number(card.dataset.price);
  item.classList.toggle('nu256-highlight',card.dataset.combo256==='1'||(price>0&&regular>price));
  if(regular>price){const badge=make('span','nu256-discount',(offer?'−':'🔥 -')+Math.round((regular-price)*100/regular)+'%');item.prepend(badge);}
  const content=make('div','nu190-card-content');content.append(make('h3','',card.dataset.name||'Produto'),make('strong','',money(Number(card.dataset.price)||0)+(card.dataset.weight370==='1'?'/kg':'')));
  if(item.classList.contains('nu275-combo-card'))item.prepend(make('span','nu284-combo-badge','COMBO'));
  if(regular>price)content.insertBefore(make('del','nu284-old-price',money(regular)),content.querySelector('strong'));
  else if(!item.classList.contains('nu275-combo-card')){
    const spacer=make('span','nu284-old-price nu487-old-slot');spacer.setAttribute('aria-hidden','true');
    content.insertBefore(spacer,content.querySelector('strong'));
  }
  if(item.classList.contains('nu275-combo-card')||offer){const priceBox=make('div','nu289-combo-price'),label=make('small','',item.classList.contains('nu275-combo-card')?'Preço do combo':'Preço promocional'),old=content.querySelector('.nu284-old-price'),value=content.querySelector('strong');priceBox.append(label);if(old)priceBox.append(old);priceBox.append(value);content.append(priceBox);}
  if(!item.classList.contains('nu275-combo-card')&&!offer){
    highlightRegularPrice(content);
    item.classList.add('nu451-regular-card');
  }
  if(card.dataset.combo256==='1'&&window.NOWUP_COMBO_PRICE303){try{const result=window.NOWUP_COMBO_PRICE303.compare(JSON.parse(card.dataset.custom192||'{}'),JSON.parse(card.dataset.comboPrices303||'{}'),price);if(result?.saving>0){content.append(make('small','nu303-separate',(result.variable?'Avulsos a partir de ':'Avulsos: ')+money(result.separate)),make('small','nu303-saving',(result.variable?'Economize a partir de ':'Economize ')+money(result.saving)));}}catch(_){}}
  const toggle=make('button','nu201-open','Adicionar');toggle.type='button';toggle.setAttribute('aria-label','Adicionar '+card.dataset.name);toggle.setAttribute('aria-expanded','false');
  const panel=make('div','nu201-panel');panel.hidden=true;
  const controls=make('div','nu190-amount'),minus=make('button','','−'),plus=make('button','','+'),amount=make('input');minus.type=plus.type='button';
  minus.setAttribute('aria-label','Diminuir quantidade');plus.setAttribute('aria-label','Aumentar quantidade');amount.type='number';amount.min='1';amount.max=String(Number(card.dataset.max)||99);amount.value='1';amount.step='1';amount.inputMode='numeric';amount.setAttribute('aria-label','Quantidade de '+card.dataset.name);controls.append(minus,amount,plus);
  const add=make('button','nu190-add','Adicionar');add.type='button';const back=make('button','nu201-back','Voltar');back.type='button';
  function normalize(){const n=Math.max(1,Math.min(Number(amount.max),Math.trunc(Number(amount.value)||1)));amount.value=String(n);minus.disabled=n<=1;plus.disabled=n>=Number(amount.max);return n;}
  function close(){panel.hidden=true;toggle.hidden=(window.NOWUP_CART160?.quantity(card.dataset.id)||0)>0;toggle.setAttribute('aria-expanded','false');item.classList.remove('nu201-selected');}
  const chosen=make('small','nu-cart-selected262');chosen.hidden=true;chosen.setAttribute('aria-live','polite');content.append(chosen);const step=make('div','nu-step263'),less=make('button','','−'),number=make('span'),more=make('button','','+');less.type=more.type='button';less.setAttribute('aria-label','Remover uma unidade de '+card.dataset.name);more.setAttribute('aria-label','Adicionar uma unidade de '+card.dataset.name);number.setAttribute('aria-live','polite');step.append(less,number,more);step.hidden=true;less.onclick=()=>window.NOWUP_CART160?.adjust(card.dataset.id,-1);more.onclick=()=>window.NOWUP_CART160?.adjust(card.dataset.id,1);
  function sync(){const count=window.NOWUP_CART160?.quantity(card.dataset.id)||0;chosen.hidden=true;step.hidden=count===0;toggle.hidden=count>0||!panel.hidden;number.textContent=card.dataset.weight370==='1'?'⚖':String(count);if(count>0){panel.hidden=true;item.classList.remove('nu201-selected');}more.disabled=!!card.querySelector('[data-add]')?.disabled||count>=Number(card.dataset.max||99);item.classList.toggle('nu-cart-in262',count>0);const blocked=!!card.querySelector('[data-add]')?.disabled;toggle.disabled=blocked;add.disabled=blocked;toggle.textContent=toggle.dataset.stockSoldOut391==='1'?'Esgotado':blocked?'Indisponível':item.classList.contains('nu275-combo-card')?'›':'Adicionar';if(item.classList.contains('nu275-combo-card')){toggle.hidden=false;step.hidden=true;}if(card.dataset.weight370==='1'){step.hidden=true;toggle.hidden=false;toggle.textContent=blocked?'Indisponível':count?'Alterar peso':'Escolher peso';}normalize();}
  function open(){if(card.dataset.weight370==='1'){window.NOWUP_WEIGHT370?.open(card);return;}if(toggle.disabled)return;if(card.querySelector('.nu151-choose')){card.querySelector('.nu151-choose').click();return;}if(card.dataset.dish!=='1'&&card.dataset.unitCombo364!=='1'&&!item.classList.contains('nu275-combo-card')&&!card.querySelector('.product-options')){const original=card.querySelector('[data-add]');if(original&&!original.disabled){const q=card.querySelector('[data-product-quantity]');if(q)q.value='1';original.click();return;}}if(item.classList.contains('nu275-combo-card')){card.querySelector('.nu151-choose')?.click();return;}panel.hidden=false;toggle.hidden=true;toggle.setAttribute('aria-expanded','true');item.classList.add('nu201-selected');normalize();}
  toggle.addEventListener('click',open);item.addEventListener('click',e=>{if(!e.target.closest('button,input,a,label')&&panel.hidden&&(item.classList.contains('nu275-combo-card')||!(window.NOWUP_CART160?.quantity(card.dataset.id)||0)))open();});
  minus.addEventListener('click',()=>{amount.value=String(normalize()-1);normalize();});plus.addEventListener('click',()=>{amount.value=String(normalize()+1);normalize();});amount.addEventListener('change',normalize);
  add.addEventListener('click',()=>{const original=card.querySelector('[data-add]');if(!original||original.disabled)return;const choose=card.querySelector('.nu151-choose');if(choose){choose.click();return;}const quantity=card.querySelector('[data-product-quantity]');if(quantity)quantity.value=String(normalize());original.click();close();});back.addEventListener('click',()=>{close();toggle.focus();});
  panel.append(controls,add,back);const actions=make('div','nu-cart-actions262');actions.append(toggle,step);if(item.classList.contains('nu275-combo-card')){toggle.classList.add('nu284-combo-open');toggle.setAttribute('aria-label','Personalizar '+card.dataset.name);step.hidden=true;}content.append(actions,panel);item.append(content);cartRefreshers.push(sync);sync();return item;
 }
 if(body.classList.contains('fashion-catalog385')&&window.NOWUP_FASHION_LAYOUT391){window.NOWUP_FASHION_LAYOUT391({root,originals,compact,sticky,nav,intro,showcase,categoryView,layout,back,cartRefreshers,search});return;}
 const buttons=nav?Array.from(nav.querySelectorAll('[data-category-filter]')):[],groups=new Map();
 // Keep category selection and its scroll container aligned without moving the page.
 function markCategory362(key){
  buttons.forEach(b=>{const active=b.dataset.categoryFilter===key;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active));});
  const button=buttons.find(b=>b.dataset.categoryFilter===key);if(!button||!nav)return;
  const bar=nav.getBoundingClientRect(),box=button.getBoundingClientRect();
  if(box.left<bar.left+8||box.right>bar.right-8)nav.scrollLeft+=box.left-bar.left-(bar.width-box.width)/2;
  if(box.top<bar.top+8||box.bottom>bar.bottom-8)nav.scrollTop+=box.top-bar.top-(bar.height-box.height)/2;
 }
 let spyFrame362=0;
 function scheduleCategory362(){if(spyFrame362)return;spyFrame362=requestAnimationFrame(()=>{
  spyFrame362=0;if(!body.classList.contains('nu187-store-home')||showcase.hidden||search.value.trim())return;
  const top=Math.max(0,sticky.getBoundingClientRect().bottom)+24;
  let current=null;for(const [key,section] of sections){const box=section.getBoundingClientRect();if(!box.height)continue;if(current===null)current=key;if(box.top<=top)current=key;else break;}
  if(current)markCategory362(current);
 });}
 window.addEventListener('scroll',scheduleCategory362,{passive:true});
 window.addEventListener('resize',scheduleCategory362);
 let swipe362=null;
 categoryView.addEventListener('touchstart',event=>{const t=event.touches[0];swipe362=event.touches.length===1&&!event.target.closest('button,a,input,textarea,select,label')?{x:t.clientX,y:t.clientY}:null;},{passive:true});
 categoryView.addEventListener('touchcancel',()=>swipe362=null,{passive:true});
 categoryView.addEventListener('touchend',event=>{const start=swipe362;swipe362=null;if(!start||!selectedCategory||search.value.trim()||document.querySelector('dialog[open]'))return;const t=event.changedTouches[0],dx=start.x-t.clientX,dy=start.y-t.clientY;if(Math.abs(dx)<60||Math.abs(dx)<Math.abs(dy)*1.5)return;const keys=[...ordered256.keys()],index=keys.indexOf(selectedCategory),next=index+(dx>0?1:-1);if(index>=0&&next>=0&&next<keys.length)showCategory(keys[next]);},{passive:true});
 root.addEventListener('keydown',event=>{const button=event.target.closest('[data-category-filter]');if(!button||!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(event.key)||(!selectedCategory&&!desktop228.matches))return;const available=buttons.filter(b=>b.isConnected&&b.dataset.categoryFilter!=='all'),index=available.indexOf(button),next=available[index+(['ArrowRight','ArrowDown'].includes(event.key)?1:-1)];if(!next)return;event.preventDefault();event.stopImmediatePropagation();showCategory(next.dataset.categoryFilter,{filter:true});next.focus({preventScroll:true});},true);

 buttons.filter(b=>b.dataset.categoryFilter!=='all').forEach(b=>groups.set(b.dataset.categoryFilter,{name:b.textContent.trim(),cards:[]}));
 const catalog275=catalogGroups275(originals);
 catalog275.regular.forEach(card=>{const key=card.dataset.category||'outros';if(!groups.has(key))groups.set(key,{name:card.querySelector('.menu-product-info small')?.textContent?.trim()||'Outros produtos',cards:[]});groups.get(key).cards.push(card);});
 const offers256=catalog275.promotions;
 const combos256=catalog275.combos;
 groups.forEach((group,key)=>{if(!group.cards.length){groups.delete(key);const b=buttons.find(b=>b.dataset.categoryFilter===key);b?.remove();}});
 const special256=new Map();
 if(combos256.length)special256.set('__combos256',{name:'Combos',cards:combos256});
 if(offers256.length)special256.set('__offers256',{name:'Promoções',cards:offers256});
 if(new URLSearchParams(location.search).get('secao')==='geladas'){const cold=originals.filter(card=>card.dataset.cold==='1'&&card.dataset.available256==='1');if(cold.length)special256.set('__cold494',{name:'Bebidas geladas',cards:cold});}
 const ordered256=new Map([...special256,...groups]);
 special256.forEach((value,key)=>groups.set(key,value));
 const categoryBar274=nav||make('nav','menu-category-nav');
 if(!nav)sticky.append(categoryBar274);
 const firstCategory274=categoryBar274.querySelector('[data-category-filter]:not([data-category-filter="all"])');
 special256.forEach((group,key)=>{const b=make('button','',group.name);b.type='button';b.dataset.categoryFilter=key;b.replaceChildren(window.NowUpCategory230.create(group.name),make('span','nu230-label',group.name));categoryBar274.insertBefore(b,firstCategory274);buttons.push(b);});
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
  const section=make('section','nu190-category');section.dataset.category190=key;section.classList.toggle('nu275-combo-section',key==='__combos256');section.classList.toggle('nu290-offers-section',key==='__offers256');sections.set(key,section);
  const header=make('header'),all=make('button','nu471-view-all','Ver todos ›');all.type='button';all.addEventListener('click',()=>showCategory(key));const title=make('h2','nu286-category-label'),icon=make('span','nu284-category-icon');icon.setAttribute('aria-hidden','true');icon.replaceChildren(window.NowUpCategory230.create(group.name));title.append(icon,document.createTextNode(group.name));header.append(title,all);section.append(header);
  if(desktop228.matches){
   all.remove();
   const grid=make('div','nu312-grid');grid.id='nu312-category-'+sections.size;
   let loaded=0;
   const limit347=group.cards.length>8?7:group.cards.length;
   const more=make('button','nu312-more');more.type='button';
   more.append(make('span','nu312-plus','+'),make('strong','','Ver todos'),make('small','','Expandir categoria'),make('span','','⌄'));
   more.setAttribute('aria-controls',grid.id);more.setAttribute('aria-expanded','false');
   const collapse347=make('button','nu347-collapse','Ver menos ⌃');collapse347.type='button';collapse347.hidden=true;
   collapse347.setAttribute('aria-controls',grid.id);collapse347.setAttribute('aria-expanded','false');collapse347.setAttribute('aria-label','Recolher produtos de '+group.name);
   if(group.cards.length>8&&!hasSubcategories261(key)){header.classList.add('nu347-category-heading');header.prepend(collapse347);}
   function load312(limit){while(loaded<Math.min(limit,group.cards.length)){grid.append(compact(group.cards[loaded++],key==='__offers256'));}}
   const controls347=catalogExpansion347({grid,more,collapseButton:collapse347,load:load312,count:group.cards.length,limit:limit347,refresh:()=>cartRefreshers.forEach(fn=>fn()),section});
   load312(limit347);
   if(group.cards.length>8||hasSubcategories261(key))grid.append(more);
   more.addEventListener('click',hasSubcategories261(key)?()=>showCategory(key):controls347.expand);collapse347.addEventListener('click',controls347.collapse);section.nuExpand312=controls347.expand;
   section.append(grid);showcase.append(section);return;
  }
  const track=make('div','nu190-track');track.tabIndex=0;
  track.setAttribute('aria-label','Produtos de '+group.name+'; deslize para os lados');
  const pages=[],pageSources238=[];
  const special=key==='__combos256'||key==='__offers256';
  const pageSize275=special?1:pageSize235;
  const columns=special?1:({large:1,three:3,six:3,eight:4})[root.dataset.carouselLayout]||2;
  for(let i=0;i<group.cards.length;i+=pageSize275){
   const page=make('div','nu190-page');
   const sources=group.cards.slice(i,i+pageSize275);
   if(sources.length<=columns)page.style.setProperty('grid-template-rows','auto','important');
   pageSources238.push(sources);pages.push(page);track.append(page);
  }
  function loadPage238(i){
   const page=pages[i];
   if(!page||page.dataset.loaded238)return;
   page.dataset.loaded238='1';
   pageSources238[i].forEach(card=>page.append(compact(card,key==='__offers256')));
  }
  loadPage238(0);loadPage238(1);
  if(key==='__offers256')pages.forEach((_,i)=>loadPage238(i));
  const carousel=make('div','nu471-carousel');
  const previous=make('button','nu471-carousel-next nu481-prev','‹');
  const next=make('button','nu471-carousel-next','›');
  previous.type=next.type='button';
  previous.hidden=next.hidden=pages.length<2;
  previous.setAttribute('aria-label','Página anterior de '+group.name);
  next.setAttribute('aria-label','Próxima página de '+group.name);
  const notice=make('p','nu481-carousel-notice');
  notice.setAttribute('role','status');
  carousel.append(track,previous,next,notice);section.append(carousel);
  const indicator=make('div','nu190-indicator'),dots=make('div','nu190-dots');
  let index=0,noticeTimer,touch,observedPage;
  const dotButtons=pages.map((_,i)=>{
   const button=make('button');button.type='button';
   button.setAttribute('aria-label','Página '+(i+1)+' de '+group.name);
   button.addEventListener('click',()=>go(i));dots.append(button);return button;
  });
  const maxScroll=()=>Math.max(0,track.scrollWidth-track.clientWidth);
  const pageLeft293=i=>Math.min(maxScroll(),Math.max(0,pages[i].offsetLeft-pages[0].offsetLeft));
  function fitPage(){
   if(special||!track.clientWidth)return;
   track.style.height=pages[index].offsetHeight+'px';
  }
  const pageObserver=typeof ResizeObserver==='function'?new ResizeObserver(fitPage):null;
  function refresh(){
   if(!track.clientWidth)return;
   const maximum=maxScroll();
   index=maximum>0&&track.scrollLeft>=maximum-2?pages.length-1:
    pages.reduce((best,_,i)=>Math.abs(track.scrollLeft-pageLeft293(i))<Math.abs(track.scrollLeft-pageLeft293(best))?i:best,0);
   loadPage238(index);loadPage238(index-1);loadPage238(index+1);
   if(observedPage!==pages[index]){
    if(observedPage)pageObserver?.unobserve(observedPage);
    observedPage=pages[index];pageObserver?.observe(observedPage);
   }
   fitPage();
   dotButtons.forEach((button,i)=>{
    button.classList.toggle('active',i===index);
    button.setAttribute('aria-current',i===index?'true':'false');
   });
   previous.hidden=next.hidden=pages.length<2||maximum<=2;
  }
  function go(i,automatic=false){
   if(pages.length<2)return;
   const wrapped=i<0||i>=pages.length;
   const target=(i+pages.length)%pages.length;
   if(wrapped&&!automatic){
    clearTimeout(noticeTimer);
    notice.textContent=i<0?'Início da lista · Indo ao final':'Fim da lista · Voltando ao início';
    noticeTimer=setTimeout(()=>{notice.textContent='';},2100);
   }
   loadPage238(target);loadPage238(target-1);loadPage238(target+1);
   track.scrollTo({left:pageLeft293(target),behavior:wrapped||matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
   if(wrapped)refresh();
  }
  previous.addEventListener('click',()=>go(index-1));next.addEventListener('click',()=>go(index+1));
  track.addEventListener('scroll',refresh,{passive:true});
  track.addEventListener('touchstart',event=>{
   const point=event.touches[0];
   touch=event.touches.length===1&&maxScroll()>2?{x:point.clientX,y:point.clientY,
    start:track.scrollLeft<=2,end:track.scrollLeft>=maxScroll()-2}:null;
  },{passive:true});
  track.addEventListener('touchcancel',()=>{touch=null;},{passive:true});
  track.addEventListener('touchend',event=>{
   const start=touch;touch=null;
   if(!start||event.touches.length)return;
   const point=event.changedTouches[0],dx=point.clientX-start.x,dy=point.clientY-start.y;
   if(Math.abs(dx)<32||Math.abs(dx)<=Math.abs(dy))return;
   if(dx<0&&start.end)go(pages.length);
   if(dx>0&&start.start)go(-1);
  },{passive:true});
  track.addEventListener('keydown',event=>{
   if(event.target!==track||!['ArrowRight','ArrowLeft'].includes(event.key))return;
   event.preventDefault();go(index+(event.key==='ArrowRight'?1:-1));
  });
  indicator.hidden=pages.length<2;
  indicator.append(dots);section.append(indicator);refreshers.push(refresh);showcase.append(section);refresh();
  if(special&&pageSize275===1&&pages.length>1)window.NowUpAutoSlide501?.attach({track,controls:section,advance:()=>go(index+1,true),enabled:()=>body.classList.contains('nu187-store-home')&&!showcase.hidden});
 });
 function filterCategory(){
  if(!selectedCategory)return;
  const entry=categoryCache.get(selectedCategory),query=search.value.trim();let count=0;
  entry.cards.forEach(({source,node})=>{const text=(source.dataset.name||'')+' '+(source.querySelector('.menu-product-info p')?.textContent||'');const found=window.NowUpSearch179?window.NowUpSearch179.matches(text,query):text.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().includes(query.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase());const match=found&&(!selectedSubcategory261||source.dataset.subcategory261===selectedSubcategory261);if(node.hidden===match)node.hidden=!match;if(match)count++;});
  const label=count+' '+(count===1?'produto':'produtos');
  if(categoryCount.textContent!==label)categoryCount.textContent=label;
  if(categoryEmpty.hidden!==(count>0))categoryEmpty.hidden=count>0;
 }
 function showCategory(key,{filter=false}={}){
  const group=groups.get(key);if(!group)return;
  activeCategory.hidden=!filter;
  if(!filter&&desktop228.matches&&!hasSubcategories261(key)&&sections.get(key)?.nuExpand312){showHome();const section=sections.get(key);section.nuExpand312();markCategory362(key);section.scrollIntoView({block:'start',behavior:'auto'});return;}
  if(body.classList.contains('nu187-store-home'))homeScroll=window.scrollY;
  const switching=selectedCategory!==null;
  selectedCategory=key;prepareSubcategories(key);body.classList.remove('nu187-store-home');body.classList.add('nu191-category');
  intro.hidden=true;showcase.hidden=true;categoryView.hidden=false;back.setAttribute('aria-label','Voltar à página da loja');
  if(nav){
   if(desktop228.matches&&anchor.nextElementSibling!==nav)anchor.after(nav);
   else if(!desktop228.matches&&nav.parentElement!==sticky)sticky.append(nav);
  }
  if(subcategoryFilters.parentElement!==sticky)sticky.append(subcategoryFilters);
  if(!categoryCache.has(key)){
   const grid=make('div','nu191-grid');grid.classList.toggle('nu275-combos-grid',key==='__combos256'||key==='__offers256');grid.classList.toggle('nu277-promotions-grid',key==='__offers256');const cards=group.cards.map(source=>{const node=compact(source,key==='__offers256');grid.append(node);return {source,node};});categoryFooter.before(grid);categoryCache.set(key,{grid,cards});
  }
  categoryCache.forEach((entry,k)=>entry.grid.hidden=k!==key);
  categoryView.classList.toggle('nu276-combo-view',key==='__combos256'||key==='__offers256');
  const viewName276=key==='__combos256'?'Combos':key==='__offers256'?'Promoções':group.name;
  categoryTitle.replaceChildren(window.NowUpCategory230.create(viewName276),document.createTextNode(viewName276));activeCategory.textContent=viewName276+' ×';activeCategory.setAttribute('aria-label','Limpar filtro de '+viewName276);if(!filter)search.value='';search.placeholder=key==='__combos256'?'Buscar combos':key==='__offers256'?'Buscar promoções':'Buscar em '+group.name;search.setAttribute('aria-label',search.placeholder);filterCategory();
  markCategory362(key);
  if(!switching)resize();
  if(window.scrollY>0)window.scrollTo({top:0,behavior:'instant'});
 }
 function searchView354(event){
  if(event.target!==search)return;
  if(selectedCategory){
    event.stopImmediatePropagation();
    filterCategory();
    return;
  }
  // Legacy target listeners stop propagation. Switch views in capture phase
  // too, so paste/autofill can search without a preceding click or keydown.
  if(body.classList.contains('nu187-store-home')&&search.value.trim())showProducts();
 }
 root.addEventListener('input',searchView354,true);
 root.addEventListener('search',searchView354,true);
 if(!originals.length)showcase.append(make('p','nu190-empty','Esta loja ainda não publicou produtos.'));
 const activeCategory=make('button','nu462-active-category');
 activeCategory.type='button';activeCategory.hidden=true;heading.after(activeCategory);
 function showAllCategories(){
  showProducts();
  markCategory362('all');
  search.dispatchEvent(new Event('input',{bubbles:true}));
 }
 activeCategory.addEventListener('click',showAllCategories);
 root.addEventListener('click',event=>{
  const button=event.target.closest('.menu-category-nav [data-category-filter]');
  if(!button)return;
  event.preventDefault();event.stopImmediatePropagation();
  if(button.dataset.categoryFilter==='all')showAllCategories();
  else if(selectedCategory!==button.dataset.categoryFilter)showCategory(button.dataset.categoryFilter,{filter:true});
 },true);
 const scrollCategories=make('button','nu462-scroll-categories','›');
 scrollCategories.type='button';scrollCategories.hidden=true;
 scrollCategories.setAttribute('aria-label','Rolar categorias para o lado');
 heading.append(scrollCategories);
 scrollCategories.addEventListener('click',()=>{
  const end=categoryBar274.scrollWidth-categoryBar274.clientWidth;
  categoryBar274.scrollTo({left:categoryBar274.scrollLeft>=end-2?0:categoryBar274.scrollLeft+categoryBar274.clientWidth*.8});
 });
 function updateCategoryArrow(){
  scrollCategories.hidden=desktop228.matches||categoryBar274.scrollWidth<=categoryBar274.clientWidth+1;
 }
 updateCategoryArrow();
 if(typeof ResizeObserver==='function')new ResizeObserver(updateCategoryArrow).observe(categoryBar274);
 // Focus alone does not switch views: explicit top-search interaction does.
 search.addEventListener('click',()=>{if(body.classList.contains('nu187-store-home'))showProducts(true);});
 search.addEventListener('keydown',event=>{if(body.classList.contains('nu187-store-home')&&(event.key==='Enter'||event.key.length===1))showProducts();});
 search.addEventListener('input',()=>{if(body.classList.contains('nu187-store-home')&&search.value)showProducts();});
 back.addEventListener('click',()=>{if(selectedCategory){collapseCategory();return;}const store=document.getElementById('store-app256');if(store){location.href=JSON.parse(store.textContent).menu;return;}if(desktop228.matches||body.classList.contains('nu187-store-home'))location.href='/';else showHome();});
 intro.querySelector('[data-store-promotion187]')?.addEventListener('click',()=>showCategory('__offers256'));
 function syncNative262(){[...originals.filter(card=>card.dataset.group260!=='1'),...root.querySelectorAll('.nu-group260-row[data-product]')].forEach(card=>{const button=card.querySelector('[data-add]');if(!button)return;let step=card.querySelector('[data-step263]');if(!step){step=make('div','nu-step263');step.dataset.step263='';const less=make('button','','−'),number=make('span'),more=make('button','','+');less.type=more.type='button';less.setAttribute('aria-label','Remover uma unidade de '+card.dataset.name);more.setAttribute('aria-label','Adicionar uma unidade de '+card.dataset.name);number.setAttribute('aria-live','polite');less.onclick=()=>window.NOWUP_CART160?.adjust(card.dataset.id,-1);more.onclick=()=>window.NOWUP_CART160?.adjust(card.dataset.id,1);step.append(less,number,more);button.after(step);}const count=window.NOWUP_CART160?.quantity(card.dataset.id)||0;step.hidden=count===0;step.querySelector('span').textContent=String(count);step.lastElementChild.disabled=button.disabled||count>=Number(card.dataset.max||99);button.hidden=count>0;if(card.dataset.weight370==='1'){step.hidden=true;button.hidden=false;button.textContent=count?'Alterar peso':'Escolher peso';}card.classList.toggle('nu-cart-in262',count>0);});}
 syncNative262();window.addEventListener('nowup-cart-changed',()=>{cartRefreshers.forEach(fn=>fn());syncNative262();});
 desktop228.addEventListener('change',()=>location.reload());
 root.dataset.categoryActions462='1';body.dataset.store187Ready='1';
 const params483=new URLSearchParams(location.search);
 const shortcut483=params483.get('secao');
 const names483={
  cervejas:['cervejas','cerveja'],
  refrigerantes:['refrigerantes','bebidas nao alcoolicas','bebidas nao alcolicas'],
  mercearia:['mercearia'],
  chocolates:['chocolates','chocolate'],
  energeticos:['energeticos','energeticos e isotônicos','bebidas nao alcoolicas','bebidas nao alcolicas'],
  destilados:['destilados','bebidas quentes','bebidas alcoolicas gerais'],
  lanches:['lanches e refeicoes','lanches'],
  combos:['combos']
 };
 const shortcutNames483=Object.hasOwn(names483,shortcut483)?names483[shortcut483]:[];
 const category483=shortcut483==='promocoes'?'__offers256':shortcut483==='combos'?'__combos256':shortcut483==='geladas'?'__cold494':shortcutNames483
  .map(name=>buttons.find(button=>normalize274(button.textContent.trim())===name)?.dataset.categoryFilter)
  .find(Boolean);
 if(params483.has('produto')||/^#produto-/.test(location.hash))showProducts();
 else if(category483&&ordered256.has(category483)){
  showCategory(category483,{filter:true});
  if(shortcut483==='refrigerantes'||shortcut483==='energeticos'){
   const subcategory=[...subcategoryFilters.querySelectorAll('button')].find(button=>normalize274(button.textContent.trim())===shortcut483);
   subcategory?.click();
  }
 }else showHome();
});

