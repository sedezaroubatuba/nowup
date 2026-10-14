(() => {
 'use strict';
 const root=document.querySelector('[data-native-menu]');
 const nav=root?.querySelector('.menu-category-nav');
 const heading=root?.querySelector('.nu83-catalog-heading');
 if(!nav||!heading||root.dataset.categories168)return;
 root.dataset.categories168='1';
 const originals=[...nav.querySelectorAll('[data-category-filter]')];
 if(!originals.length)return;
 const dialog=document.createElement('dialog');
 dialog.className='nu168-categories';dialog.id='nu168-categories';
 dialog.setAttribute('aria-labelledby','nu168-title');
 const header=document.createElement('header');
 const title=document.createElement('h2');title.id='nu168-title';title.textContent='Categorias';
 const close=document.createElement('button');close.type='button';close.textContent='×';close.setAttribute('aria-label','Fechar categorias');
 header.append(title,close);dialog.append(header);
 const list=document.createElement('nav');list.setAttribute('aria-label','Categorias da loja');dialog.append(list);
 const trigger=document.createElement('button');trigger.type='button';trigger.className='nu168-trigger';trigger.textContent='☰';trigger.setAttribute('aria-label','Abrir categorias');trigger.setAttribute('aria-controls',dialog.id);trigger.setAttribute('aria-expanded','false');heading.prepend(trigger);
 document.body.append(dialog);
 const entries=originals.map(original=>{
  const button=document.createElement('button');button.type='button';button.textContent=original.textContent.trim();
  button.addEventListener('click',()=>{dialog.close();original.click();original.focus({preventScroll:true});});list.append(button);return {original,button};
 });
 function sync(){entries.forEach(({original,button})=>{const active=original.classList.contains('active');button.classList.toggle('active',active);button.setAttribute('aria-pressed',String(active));});}
 function open(opener=trigger){sync();dialog.showModal();trigger.setAttribute('aria-expanded','true');dialog.dataset.opener=opener===trigger?'catalog':'site';document.documentElement.classList.add('nu168-menu-open');close.focus();}
 trigger.addEventListener('click',()=>open());close.addEventListener('click',()=>dialog.close());
 dialog.addEventListener('close',()=>{trigger.setAttribute('aria-expanded','false');document.documentElement.classList.remove('nu168-menu-open');trigger.focus({preventScroll:true});});
 dialog.addEventListener('click',event=>{if(event.target!==dialog)return;const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();});
 document.addEventListener('click',event=>{const button=event.target.closest('[data-nowup-menu-open]');if(button&&document.body.classList.contains('nu145-browsing')){event.preventDefault();event.stopImmediatePropagation();open(button);}},true);
 new MutationObserver(sync).observe(nav,{subtree:true,attributes:true,attributeFilter:['class']});
})();
