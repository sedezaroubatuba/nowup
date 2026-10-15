/* V181: catalog-only return controls; does not move products or change filtering. */
(()=>{'use strict';
 const start=()=>{
  const root=document.querySelector('[data-native-menu]');if(!root||root.dataset.return181)return;
  const nav=root.querySelector('.menu-category-nav'),products=root.querySelector('.menu-products');if(!nav||!products)return;root.dataset.return181='1';
  const go=()=>{const sticky=root.querySelector('.nu-menu-sticky');const target=products.getBoundingClientRect().top+window.scrollY-(sticky?.getBoundingClientRect().height||100)-12;window.scrollTo({top:Math.max(0,target),behavior:'auto'});};
  function add(parent,cls,label){if(parent.querySelector('.'+cls))return;const button=document.createElement('button');button.type='button';button.className=cls;button.textContent=label;button.addEventListener('click',go);parent.append(button);}
  add(nav,'nu167-categories-return','↑ Início');
  // Sibling of the grid: never treated as a product by category rotation.
  if(!root.querySelector('.nu167-products-return')){const button=document.createElement('button');button.type='button';button.className='nu167-products-return';button.textContent='↑ Voltar ao início dos produtos';button.addEventListener('click',go);products.after(button);}
 };
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
