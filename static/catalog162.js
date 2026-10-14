(()=>{
 'use strict';
 const root=document.querySelector('[data-native-menu]');if(!root)return;
 const heading=root.querySelector('.nu83-catalog-heading'),summary=root.querySelector('[data-cart-summary]');
 if(heading&&summary){
 const button=document.createElement('button');button.type='button';button.className='nu162-top-cart';button.setAttribute('aria-label','Abrir carrinho');
 button.innerHTML='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M2 3h3l2.5 12h11l2-8H6"/><circle cx="9" cy="20" r="1"/><circle cx="18" cy="20" r="1"/></svg><span>0</span>';
 button.addEventListener('click',()=>summary.click());heading.append(button);
 const count=root.querySelector('[data-cart-count]');const refresh=()=>{const n=parseInt(count?.textContent||'0',10)||0;button.querySelector('span').textContent=String(n);button.setAttribute('aria-label',`Abrir carrinho: ${n} ${n===1?'item':'itens'}`);};
 if(count)new MutationObserver(refresh).observe(count,{childList:true,characterData:true,subtree:true});refresh();
 }
 root.querySelectorAll('.menu-products>[data-product]').forEach(card=>{
 const add=card.querySelector('[data-add]');if(add){const set=()=>{if(!add.disabled&&!card.classList.contains('nu151-dish-open')){if(add.textContent!=='+')add.textContent='+';add.setAttribute('aria-label','Adicionar '+card.dataset.name);}};new MutationObserver(set).observe(add,{childList:true});set();}
 if(card.dataset.dish==='1'&&card.querySelector('[data-product-option]')){const badge=document.createElement('small');badge.className='nu162-extra-badge';badge.textContent='Adicionais disponíveis';card.querySelector('.menu-product-info>p')?.after(badge);}
 });
})();
