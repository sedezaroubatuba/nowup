/* Suggestions reuse original product actions and checkout price validation. */
function selectPairs256(products,inCart){
 if(!inCart.size)return [];
 const byId=new Map(products.map(p=>[p.id,p])),candidates=new Set();
 products.filter(p=>p.recommend).forEach(p=>candidates.add(p.id));
 inCart.forEach(id=>(byId.get(id)?.related||'').split(',').filter(Boolean).forEach(id=>candidates.add(id)));
 return [...candidates].filter(id=>!inCart.has(id)&&byId.has(id)&&!byId.get(id).blocked).slice(0,5);
}
if(typeof module!=='undefined')module.exports={selectPairs256};
if(typeof document!=='undefined')document.addEventListener('DOMContentLoaded',()=>{
 'use strict';
 const root=document.querySelector('[data-native-menu]'),dialog=root?.querySelector('[data-cart-dialog143]'),items=root?.querySelector('[data-cart-items]');
 if(!dialog||!items)return;
 const products=[...root.querySelectorAll('[data-product]')],byId=new Map(products.map(p=>[p.dataset.id,p]));
 const box=document.createElement('section');box.className='nu256-pairs';box.setAttribute('aria-label','Leve junto');items.after(box);
 const money=n=>(Number(n)/100).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
 let signature='';
 function refresh(){
  const inCart=new Set([...items.querySelectorAll('[data-cart-quantity]')].map(el=>el.dataset.cartQuantity.split(':')[0]));
  const chosen=selectPairs256(products.map(p=>({id:p.dataset.id,related:p.dataset.related256||'',recommend:p.dataset.recommend256==='1',blocked:p.dataset.available256==='0'||!p.querySelector('[data-add]')||p.querySelector('[data-add]').disabled})),inCart);
  const next=JSON.stringify(chosen.map(id=>[id,byId.get(id).dataset.price,byId.get(id).dataset.name]));
  if(signature===next)return;signature=next;
  box.replaceChildren();box.hidden=!chosen.length;if(!chosen.length)return;
  const header=document.createElement('header');header.className='nu310-pairs-heading';
  const heading=document.createElement('div'),title=document.createElement('h3'),subtitle=document.createElement('small'),counter=document.createElement('span');title.textContent='✨ Leve junto';subtitle.textContent='Sugestões da loja';heading.append(title,subtitle);counter.textContent=chosen.length>2?'1/'+chosen.length:chosen.length+' sugest'+(chosen.length===1?'ão':'ões');counter.className='nu310-pair-counter';header.append(heading,counter);
  const track=document.createElement('div');track.className='nu310-pair-track';track.tabIndex=0;track.setAttribute('role','region');track.setAttribute('aria-label','Produtos sugeridos pela loja; deslize para os lados');box.append(header,track);
  chosen.forEach(id=>{
   const source=byId.get(id),row=document.createElement('article');row.className='nu256-pair';row.dataset.pair310=id;
   const photo=source.querySelector('img');if(!photo)row.classList.add('nu310-no-photo');if(photo){const img=document.createElement('img');if(photo.dataset.src258){img.src='/static/product-placeholder.svg';img.dataset.src258=photo.dataset.src258;}else img.src=photo.src;img.alt='';row.append(img);}
   const info=document.createElement('div'),name=document.createElement('b'),price=document.createElement('span');name.textContent=source.dataset.name;name.title=source.dataset.name;price.textContent=money(source.dataset.price)+(source.dataset.weight370==='1'?'/kg':'');price.className='nu371-price';info.append(name);
   const add=document.createElement('button');add.type='button';add.textContent='+ Adicionar';add.setAttribute('aria-label','Adicionar '+source.dataset.name);
   add.addEventListener('click',()=>{
    if(source.dataset.weight370==='1'){window.NOWUP_WEIGHT370?.open(source);return;}
    const custom=source.querySelector('.nu151-choose');
    if(custom){dialog.close();custom.click();return;}
    // Required choices must use the existing personalization flow.
    if(source.dataset.dish==='1'||source.querySelector('[data-product-option]')){
     dialog.close();const search=root.querySelector('[data-product-search]');if(search){search.click();search.value=source.dataset.name;search.dispatchEvent(new Event('input',{bubbles:true}));}source.hidden=false;source.querySelector('[data-product-quantity]')?.focus();source.scrollIntoView({block:'center'});return;
    }
    const qty=source.querySelector('[data-product-quantity]');if(qty)qty.value='1';source.querySelector('[data-add]')?.click();
   });
   row.append(info,price,add);track.append(row);
  });
  if(chosen.length>2){
   const controls=document.createElement('nav');controls.className='nu310-pair-controls';controls.setAttribute('aria-label','Navegar nas sugestões');
   const previous=document.createElement('button'),next=document.createElement('button'),dots=document.createElement('div');dots.className='nu310-pair-dots';previous.type=next.type='button';previous.textContent='‹';next.textContent='›';previous.setAttribute('aria-label','Sugestão anterior');next.setAttribute('aria-label','Próxima sugestão');
   let index=0;const cards=[...track.children],buttons=[];
   function paint(){counter.textContent=(index+1)+'/'+chosen.length;previous.disabled=index===0;next.disabled=index===chosen.length-1;buttons.forEach((b,i)=>b.setAttribute('aria-current',String(i===index)));}
   function go(i){index=Math.max(0,Math.min(chosen.length-1,i));const card=cards[index];track.scrollTo({left:card.offsetLeft-track.offsetLeft-(track.clientWidth-card.offsetWidth)/2,behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});paint();}
   cards.forEach((card,i)=>{const dot=document.createElement('button');dot.type='button';dot.className='nu310-pair-dot';dot.setAttribute('aria-label','Ver sugestão '+(i+1)+': '+byId.get(chosen[i]).dataset.name);dot.onclick=()=>go(i);buttons.push(dot);dots.append(dot);});
   previous.onclick=()=>go(index-1);next.onclick=()=>go(index+1);controls.append(previous,dots,next);box.append(controls);paint();
   let scrolling=false;track.addEventListener('scroll',()=>{if(scrolling)return;scrolling=true;requestAnimationFrame(()=>{scrolling=false;if(track.scrollLeft<=1)index=0;else if(track.scrollLeft+track.clientWidth>=track.scrollWidth-1)index=cards.length-1;else{const center=track.scrollLeft+track.clientWidth/2;index=cards.reduce((best,c,i)=>Math.abs(c.offsetLeft-track.offsetLeft+c.offsetWidth/2-center)<Math.abs(cards[best].offsetLeft-track.offsetLeft+cards[best].offsetWidth/2-center)?i:best,0);}paint();});},{passive:true});
  }
 }
 let pending=false;const schedule=()=>{if(!pending){pending=true;requestAnimationFrame(()=>{pending=false;refresh();});}};
 new MutationObserver(schedule).observe(items,{childList:true,subtree:true});window.addEventListener('nowup-cart-changed',schedule);dialog.addEventListener('toggle',schedule);refresh();
});

