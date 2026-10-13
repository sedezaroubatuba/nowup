(() => {
 'use strict';
 const root=document.querySelector('[data-native-menu]');
 if(!root||root.dataset.swipeReady)return;
 const heading=root.querySelector('.nu83-catalog-heading'),nav=root.querySelector('.menu-category-nav'),products=root.querySelector('.menu-products');
 if(!heading||!nav||!products)return;
 root.dataset.swipeReady='1';
 const bar=document.createElement('div');bar.className='nu-menu-sticky';
 heading.before(bar);bar.append(heading,nav);
 const hint=document.createElement('p');hint.className='nu-swipe-hint';hint.textContent='Deslize sobre os produtos para trocar de categoria ↔';bar.after(hint);
 const buttons=[...nav.querySelectorAll('[data-category-filter]')];
 const desktop=matchMedia('(min-width:1100px)');
 const firstCategory=buttons.find(b=>b.dataset.categoryFilter!=='all');
 if(firstCategory)firstCategory.click();
 const announce=document.createElement('span');announce.className='nu-swipe-announcement';announce.setAttribute('role','status');bar.append(announce);
 function reveal(button){
  const left=button.offsetLeft-(nav.clientWidth-button.offsetWidth)/2;
  nav.scrollTo({left:Math.max(0,left),behavior:'instant'});
  announce.textContent='Categoria: '+button.textContent.trim();
 }
 nav.addEventListener('click',e=>{const b=e.target.closest('[data-category-filter]');if(b)reveal(b);});
 // Soma somente cabeçalhos fixos da aplicação, sem usar altura do conteúdo rolável.
 const anchor=document.createElement('div');anchor.className='nu-search-anchor';bar.before(anchor);
 const search=bar.querySelector('[data-product-search]');
 let queued=false;
 function offset(){
  queued=false;
  const header=document.querySelector('header.top,.top');let top=window.visualViewport?.offsetTop||0;
  if(header){const cs=getComputedStyle(header);if(['fixed','sticky'].includes(cs.position)){const rect=header.getBoundingClientRect();if(rect.top<=top+1)top=Math.max(top,rect.bottom);}}
  const rect=anchor.getBoundingClientRect(),end=root.getBoundingClientRect().bottom;
  const focused=document.activeElement===search;
  const fixed=(rect.top<=top||focused)&&end>top+bar.offsetHeight;
  bar.classList.toggle('nu-search-fixed',fixed);
  anchor.style.height=fixed?bar.offsetHeight+'px':'0px';
  bar.style.setProperty('--nu-sticky-top',top+'px');
  if(fixed){bar.style.left=rect.left+'px';bar.style.width=rect.width+'px';}
  else{bar.style.left='';bar.style.width='';}
  root.classList.toggle('nu-search-focused',focused);
 }
 function schedule(){if(!queued){queued=true;requestAnimationFrame(offset);}}
 function showResults(){
  if(document.activeElement!==search)return;
  offset();
  const first=[...products.querySelectorAll('[data-product]')].find(p=>!p.hidden);
  if(!first)return;
  const bottom=bar.getBoundingClientRect().bottom;
  const delta=first.getBoundingClientRect().top-bottom-8;
  if(Math.abs(delta)>2)window.scrollBy({top:delta,behavior:'auto'});
  schedule();
 }
 offset();window.addEventListener('resize',schedule);window.addEventListener('scroll',schedule,{passive:true});
 window.visualViewport?.addEventListener('resize',()=>{schedule();requestAnimationFrame(showResults);});
 window.visualViewport?.addEventListener('scroll',schedule);
 search?.addEventListener('focus',()=>{offset();requestAnimationFrame(showResults);});
 search?.addEventListener('input',()=>requestAnimationFrame(showResults));
 search?.addEventListener('blur',schedule);
 if(typeof ResizeObserver!=='undefined')new ResizeObserver(schedule).observe(bar);
 let start=null;
 const controls='input,textarea,select,button,a,label,summary,[contenteditable="true"]';
 products.addEventListener('pointerdown',e=>{if(desktop.matches||!e.isPrimary||e.pointerType==='mouse'||e.target.closest(controls))return;start={id:e.pointerId,x:e.clientX,y:e.clientY};},{passive:true});
 products.addEventListener('pointercancel',()=>start=null,{passive:true});
 function swipe(e){
  if(!start||e.pointerId!==start.id)return;
  const dx=e.clientX-start.x,dy=e.clientY-start.y;
  if(Math.abs(dy)>18&&Math.abs(dy)>Math.abs(dx)){start=null;return;}
  if(Math.abs(dx)<38||Math.abs(dx)<Math.abs(dy)*1.7)return;
  start=null;
  const current=Math.max(0,buttons.findIndex(b=>b.classList.contains('active')));
  const target=current+(dx<0?1:-1);if(target<0||target>=buttons.length)return;
  buttons[target].click();
  // Recomeça a lista da nova categoria mantendo a barra visível.
  const top=products.getBoundingClientRect().top+window.scrollY-bar.offsetHeight-parseFloat(bar.style.getPropertyValue('--nu-sticky-top')||0)-12;
  window.scrollTo({top:Math.max(0,top),behavior:'instant'});
 }
 products.addEventListener('pointermove',swipe,{passive:true});
 products.addEventListener('pointerup',e=>{swipe(e);start=null;},{passive:true});
})();

