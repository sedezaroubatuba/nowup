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
 const groups=new Map();
 const cards=[...products.querySelectorAll('[data-product]')];
 for(const card of cards){
  const key=card.dataset.category||'';
  let group=groups.get(key);
  if(!group){
   const section=document.createElement('section');section.className='nu-desktop-category';
   const title=document.createElement('h3');title.className='nu-desktop-category-title';
   title.textContent=card.querySelector('.menu-product-info > small')?.textContent.trim()||'Outros produtos';
   section.append(title);products.append(section);
   group={section,cards:[]};groups.set(key,group);
  }
  group.section.append(card);group.cards.push(card);
 }
 function updateGroups(){
  for(const group of groups.values())group.section.hidden=!group.cards.some(card=>!card.hidden);
 }
 const observer=new MutationObserver(updateGroups);
 for(const card of cards)observer.observe(card,{attributes:true,attributeFilter:['hidden']});
 updateGroups();
 function mode(){for(const card of cards){if(desktop.matches)groups.get(card.dataset.category||'').section.append(card);else products.append(card);}updateGroups();hint.textContent=desktop.matches?'Categorias lado a lado. Use a busca ou selecione uma categoria.':'Deslize sobre os produtos para trocar de categoria ↔';}
 desktop.addEventListener('change',mode);mode();
 const reduce=()=>matchMedia('(prefers-reduced-motion: reduce)').matches;
 const announce=document.createElement('span');announce.className='nu-swipe-announcement';announce.setAttribute('role','status');bar.append(announce);
 function reveal(button){button.scrollIntoView({block:'nearest',inline:'center',behavior:reduce()?'auto':'smooth'});announce.textContent='Categoria: '+button.textContent.trim();}
 nav.addEventListener('click',e=>{const b=e.target.closest('[data-category-filter]');if(b)reveal(b);});
 // Soma somente cabeçalhos fixos da aplicação, sem usar altura do conteúdo rolável.
 function offset(){const header=document.querySelector('header.top,.top');let top=0;if(header){const cs=getComputedStyle(header);if(['fixed','sticky'].includes(cs.position)){const rect=header.getBoundingClientRect();if(rect.top<=1)top=Math.max(0,rect.bottom);}}bar.style.setProperty('--nu-sticky-top',top+'px');}
 offset();window.addEventListener('resize',offset);window.addEventListener('scroll',offset,{passive:true});
 let start=null;
 const controls='input,textarea,select,button,a,label,summary,[contenteditable="true"]';
 products.addEventListener('pointerdown',e=>{if(desktop.matches||!e.isPrimary||e.pointerType==='mouse'||e.target.closest(controls))return;start={id:e.pointerId,x:e.clientX,y:e.clientY};},{passive:true});
 products.addEventListener('pointercancel',()=>start=null,{passive:true});
 products.addEventListener('pointerup',e=>{
  if(!start||e.pointerId!==start.id)return;
  const dx=e.clientX-start.x,dy=e.clientY-start.y;start=null;
  if(Math.abs(dx)<65||Math.abs(dx)<Math.abs(dy)*1.7)return;
  const current=Math.max(0,buttons.findIndex(b=>b.classList.contains('active')));
  const target=current+(dx<0?1:-1);if(target<0||target>=buttons.length)return;
  buttons[target].click();
  // Recomeça a lista da nova categoria mantendo a barra visível.
  const top=products.getBoundingClientRect().top+window.scrollY-bar.offsetHeight-parseFloat(bar.style.getPropertyValue('--nu-sticky-top')||0)-12;
  window.scrollTo({top:Math.max(0,top),behavior:reduce()?'auto':'smooth'});
 },{passive:true});
})();
