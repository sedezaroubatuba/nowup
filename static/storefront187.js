/* Store presentation uses the existing catalogue nodes and cart engine. */
document.addEventListener('DOMContentLoaded',()=>{
 'use strict';
 const body=document.body,root=document.querySelector('[data-native-menu]');
 const template=document.getElementById('nu187-store-template');
 const heading=root?.querySelector('.nu83-catalog-heading'),layout=root?.querySelector('.menu-layout');
 const search=heading?.querySelector('[data-product-search], [data-store-search]');
 if(!root||!template||!heading||!layout||!search){body.classList.remove('nu187-store-home');return;}
 const intro=template.content.firstElementChild.cloneNode(true);
 const nav=root.querySelector('.menu-category-nav');
 const sticky=root.querySelector('.nu-menu-sticky')||heading.parentElement;
 const navAnchor=document.createComment('store-category-position189');layout.before(navAnchor);
 const back=document.createElement('button');back.type='button';back.className='nu187-back';back.textContent='←';back.setAttribute('aria-label','Voltar às informações da loja');heading.prepend(back);
 navAnchor.before(intro);body.dataset.store187Ready='1';
 let homeScroll=0;
 const resize=()=>window.dispatchEvent(new Event('resize'));
 const showProducts=(focus=false)=>{
  if(body.classList.contains('nu187-store-home'))homeScroll=scrollY;
  intro.hidden=true;back.setAttribute('aria-label','Voltar às informações da loja');if(nav)sticky.append(nav);
  body.classList.remove('nu187-store-home');search.placeholder='Buscar nesta loja';
  resize();window.scrollTo({top:0,behavior:'instant'});
  if(focus)search.focus({preventScroll:true});
 };
 const showHome=()=>{
  intro.hidden=false;body.classList.add('nu187-store-home');back.setAttribute('aria-label','Voltar ao início do NowUp');
  if(nav)navAnchor.after(nav);
  search.value='';search.dispatchEvent(new Event('input',{bubbles:true}));search.placeholder='Pesquisar produtos';search.blur();
  resize();window.scrollTo({top:homeScroll,behavior:'instant'});
 };
 const openCategory=value=>{showProducts();const button=nav&&Array.from(nav.querySelectorAll('[data-category-filter]')).find(b=>b.dataset.categoryFilter===value);button?.click();};
 search.addEventListener('focus',()=>{if(body.classList.contains('nu187-store-home'))showProducts();});
 search.addEventListener('click',()=>{if(body.classList.contains('nu187-store-home'))showProducts(true);});
 back.addEventListener('click',()=>{if(body.classList.contains('nu187-store-home')){location.href='/';}else showHome();});
 intro.querySelectorAll('[data-store-category187]').forEach(button=>button.addEventListener('click',()=>openCategory(button.dataset.storeCategory187)));
 intro.querySelector('[data-store-promotion187]')?.addEventListener('click',()=>openCategory('all'));
 // Category clicks in the presentation keep the normal page scroll.
 nav?.addEventListener('click',event=>{if(event.target.closest('[data-category-filter]')&&body.classList.contains('nu187-store-home'))layout.scrollIntoView({block:'start',behavior:'auto'});});
 // The existing category drawer remains usable from the initial search bar.
 root.addEventListener('click',event=>{if(event.target.closest('.nu168-trigger')&&body.classList.contains('nu187-store-home'))showProducts();},true);
 if(new URLSearchParams(location.search).has('produto')||/^#produto-/.test(location.hash))showProducts();else showHome();
});
