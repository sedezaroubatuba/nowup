/* Suggestions reuse original product actions and checkout price validation. */
function selectPairs256(products,inCart){
 const byId=new Map(products.map(p=>[p.id,p])),candidates=new Set();
 inCart.forEach(id=>(byId.get(id)?.related||'').split(',').filter(Boolean).forEach(id=>candidates.add(id)));
 if(inCart.size)products.filter(p=>p.recommend&&p.price<p.regular).forEach(p=>candidates.add(p.id));
 return [...candidates].filter(id=>!inCart.has(id)&&byId.has(id)&&!byId.get(id).blocked).slice(0,3);
}
if(typeof module!=='undefined')module.exports={selectPairs256};
if(typeof document!=='undefined')document.addEventListener('DOMContentLoaded',()=>{
 'use strict';
 const root=document.querySelector('[data-native-menu]'),dialog=root?.querySelector('[data-cart-dialog143]'),items=root?.querySelector('[data-cart-items]');
 if(!dialog||!items)return;
 const products=[...root.querySelectorAll('[data-product]')],byId=new Map(products.map(p=>[p.dataset.id,p]));
 const box=document.createElement('section');box.className='nu256-pairs';box.setAttribute('aria-label','Leve junto');items.after(box);
 const money=n=>(Number(n)/100).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
 function refresh(){
  const inCart=new Set([...items.querySelectorAll('[data-cart-quantity]')].map(el=>el.dataset.cartQuantity.split(':')[0]));
  const chosen=selectPairs256(products.map(p=>({id:p.dataset.id,related:p.dataset.related256||'',recommend:p.dataset.recommend256==='1',price:Number(p.dataset.price),regular:Number(p.dataset.regular256),blocked:!p.querySelector('[data-add]')||p.querySelector('[data-add]').disabled})),inCart);
  box.replaceChildren();box.hidden=!chosen.length;if(!chosen.length)return;
  const title=document.createElement('h3');title.textContent='✨ Leve junto';box.append(title);
  chosen.forEach(id=>{
   const source=byId.get(id),row=document.createElement('div');row.className='nu256-pair';
   const photo=source.querySelector('img');if(photo){const img=document.createElement('img');img.src=photo.src;img.alt='';row.append(img);}
   const info=document.createElement('div'),name=document.createElement('b'),price=document.createElement('span');name.textContent=source.dataset.name;price.textContent=money(source.dataset.price);info.append(name,price);
   const add=document.createElement('button');add.type='button';add.textContent='+ Adicionar';add.setAttribute('aria-label','Adicionar '+source.dataset.name);
   add.addEventListener('click',()=>{
    const custom=source.querySelector('.nu151-choose');
    if(custom){dialog.close();custom.click();return;}
    // Required choices must use the existing personalization flow.
    if(source.dataset.dish==='1'||source.querySelector('[data-product-option]')){
     dialog.close();const search=root.querySelector('[data-product-search]');if(search){search.click();search.value=source.dataset.name;search.dispatchEvent(new Event('input',{bubbles:true}));}source.hidden=false;source.querySelector('[data-product-quantity]')?.focus();source.scrollIntoView({block:'center'});return;
    }
    const qty=source.querySelector('[data-product-quantity]');if(qty)qty.value='1';source.querySelector('[data-add]')?.click();
   });
   row.append(info,add);box.append(row);
  });
 }
 let pending=false;const schedule=()=>{if(!pending){pending=true;requestAnimationFrame(()=>{pending=false;refresh();});}};
 new MutationObserver(schedule).observe(items,{childList:true,subtree:true});window.addEventListener('nowup-cart-changed',schedule);dialog.addEventListener('toggle',schedule);refresh();
});
