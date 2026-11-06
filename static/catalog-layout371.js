/* One collapse control follows the expanded category, without cloning its products. */
document.addEventListener('DOMContentLoaded',()=>{
 'use strict';
 const root=document.querySelector('[data-native-menu]');if(!root)return;
 const sticky=root.querySelector('.nu-menu-sticky');
 const floating=document.createElement('button');floating.type='button';floating.className='nu371-floating-collapse';floating.textContent='Ver menos ⌃';floating.hidden=true;document.body.append(floating);
 let source=null,queued=false,fitQueued=false;
 function fitPrices(){fitQueued=false;root.querySelectorAll('.nu190-card-content strong,.nu190-card-content del,.nu371-price').forEach(price=>{
  if(!price.getClientRects().length||price.clientWidth<1)return;
  price.style.removeProperty('font-size');
  const base=parseFloat(getComputedStyle(price).fontSize),available=price.clientWidth;
  if(price.scrollWidth>available+1){let size=base;while(price.scrollWidth>available+1&&size>11){size-=.5;price.style.setProperty('font-size',size+'px','important');}}
 });}
 function update(){
  queued=false;source=null;
  if(document.querySelector('dialog[open]')){floating.hidden=true;return;}
  const bar=sticky?.getBoundingClientRect(),style=sticky?getComputedStyle(sticky):null,stuck=bar&&(style.position==='fixed'||style.position==='sticky'&&bar.top<=(parseFloat(style.top)||0)+2),top=Math.max(8,stuck?bar.bottom+8:8);
  const mobileView=root.querySelector('.nu191-category-view:not([hidden])');
  const candidates=mobileView?[mobileView.querySelector('.nu219-less')]:[...root.querySelectorAll('.nu190-category .nu347-collapse:not([hidden])')];
  for(const button of candidates){if(!button||!button.getClientRects().length)continue;const section=button.closest('.nu191-category-view,.nu190-category'),bounds=section.getBoundingClientRect(),rect=button.getBoundingClientRect();if(rect.bottom<top&&bounds.bottom>top+55){source=button;break;}}
  floating.hidden=!source;if(!source)return;
  const section=source.closest('.nu191-category-view,.nu190-category'),box=section.getBoundingClientRect();
  floating.style.setProperty('top',Math.ceil(top)+'px','important');floating.style.setProperty('left',Math.max(12,Math.min(innerWidth-150,Math.ceil(box.left)))+'px','important');
  floating.setAttribute('aria-label',source.getAttribute('aria-label')||'Recolher produtos e voltar às categorias');
  if(source.getAttribute('aria-controls'))floating.setAttribute('aria-controls',source.getAttribute('aria-controls'));else floating.removeAttribute('aria-controls');
 }
 function schedule(){if(!queued){queued=true;requestAnimationFrame(update);}}
 function changed(){schedule();if(!fitQueued){fitQueued=true;requestAnimationFrame(fitPrices);}}
 floating.addEventListener('click',()=>{const button=source;floating.hidden=true;source=null;button?.click();changed();});
 window.addEventListener('scroll',schedule,{passive:true});window.addEventListener('resize',changed);window.addEventListener('click',schedule,{passive:true});window.addEventListener('keyup',schedule);window.addEventListener('nowup-cart-changed',changed);
 new MutationObserver(changed).observe(root,{subtree:true,childList:true,attributes:true,attributeFilter:['class','hidden','aria-expanded']});changed();
});
