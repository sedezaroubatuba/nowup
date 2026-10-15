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
  if(document.body.classList.contains("nu187-store-home")){queued=false;return;}
  queued=false;
  const top=window.visualViewport?.offsetTop||0;
  const rect=anchor.getBoundingClientRect(),end=root.getBoundingClientRect().bottom;
  const focused=document.activeElement===search;
  const fixed=(rect.top<=top||focused)&&end>top+bar.offsetHeight;
  bar.classList.toggle('nu-search-fixed',fixed);
  document.body.classList.toggle('nu145-browsing',fixed);
  anchor.style.height=fixed?bar.offsetHeight+'px':'0px';
  bar.style.setProperty('--nu-sticky-top',top+'px');
  if(fixed){bar.style.left=rect.left+'px';bar.style.width=rect.width+'px';}
  else{bar.style.left='';bar.style.width='';}
  root.classList.toggle('nu-search-focused',focused);
 }
 function schedule(){if(!queued){queued=true;requestAnimationFrame(offset);}}
 function showResults(){if(document.body.classList.contains("nu187-store-home"))return;
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
})();
