(() => {
  'use strict';
  const manager=document.querySelector('#categorias-loja');
  const save=manager?.querySelector('[data-save-order142]');
  save?.addEventListener('click',async()=>{
    const fields=[...manager.querySelectorAll('[data-category-position142]')];
    const status=manager.querySelector('[data-order-status142]');
    const values=fields.map(x=>Number(x.value));
    if(values.some(x=>!Number.isInteger(x)||x<1||x>fields.length)||new Set(values).size!==fields.length){status.textContent='Use cada posição de 1 a '+fields.length+' uma única vez.';return;}
    const ordered=fields.slice().sort((a,b)=>Number(a.value)-Number(b.value));
    save.disabled=true;status.textContent='Salvando ordem…';
    try{
      const body=new URLSearchParams({order_json:JSON.stringify(ordered.map(x=>Number(x.dataset.categoryPosition142)))});
      const response=await fetch('/painel/cardapio/ordem-categorias',{method:'POST',credentials:'same-origin',body});
      const data=await response.json();
      if(!response.ok||!data.ok)throw new Error(data.detail||'Não foi possível salvar. Tente novamente.');
      const list=manager.querySelector('.category-admin-list');
      ordered.forEach(x=>list.append(x.closest('.category-admin-row')));
      const select=document.querySelector('#novo-produto select[name="category"]');
      if(select){const selected=select.value;ordered.forEach(x=>{const row=x.closest('.category-admin-row');const name=row.querySelector('input[name="name"]').value;const option=[...select.options].find(o=>o.value===name);if(option)select.append(option);});select.value=selected;}
      status.textContent='Ordem salva!';
    }catch(error){status.textContent=error.message;}
    finally{save.disabled=false;}
  });
  const root=document.querySelector('[data-native-menu]');
  const nav=root?.querySelector('.menu-category-nav');
  if(!nav)return;
  const products=[...root.querySelectorAll('[data-product]')];
  const buttons=[...nav.querySelectorAll('[data-category-filter]')];
  const categories=buttons.filter(b=>b.dataset.categoryFilter!=='all'&&products.some(p=>p.dataset.category===b.dataset.categoryFilter));
  if(!categories.length)return;
  const search=root.querySelector('[data-product-search], [data-store-search]');
  let active=buttons.find(b=>b.classList.contains('active'))?.dataset.categoryFilter||'all';
  let lastSwitch=0, lastY=window.scrollY, touch=null;
  const normalize=s=>(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  function filter(){const term=normalize(search?.value);products.forEach(p=>{p.hidden=(active!=='all'&&p.dataset.category!==active)||!normalize(p.dataset.name+' '+p.textContent).includes(term);});buttons.forEach(b=>{b.classList.toggle('active',b.dataset.categoryFilter===active);b.setAttribute('aria-pressed',String(b.dataset.categoryFilter===active));});}
  function choose(button,scroll){active=button.dataset.categoryFilter;filter();button.scrollIntoView({block:'nearest',inline:'nearest',behavior:'auto'});lastSwitch=Date.now();if(scroll){const first=products.find(p=>!p.hidden);if(first){window.scrollTo({top:Math.max(0,first.getBoundingClientRect().top+window.scrollY-100),behavior:'instant'});lastY=window.scrollY;}}}
  nav.addEventListener('click',event=>{const button=event.target.closest('[data-category-filter]');if(!button)return;event.preventDefault();event.stopImmediatePropagation();choose(button,true);},true);
  search?.addEventListener('input',()=>{active='all';filter();},true);
  function next(direction=1){if(categories.length<2||search?.value.trim()||document.querySelector('dialog[open]')||Date.now()-lastSwitch<800)return;const index=categories.findIndex(b=>b.dataset.categoryFilter===active);choose(categories[(index+direction+categories.length)%categories.length],true);}
  function atEnd(){const visible=products.filter(p=>!p.hidden);return visible.length&&visible[visible.length-1].getBoundingClientRect().bottom<=window.innerHeight-70;}
  window.addEventListener('scroll',()=>{const y=window.scrollY;if(y>lastY+2&&atEnd())next();lastY=window.scrollY;},{passive:true});
  window.addEventListener('wheel',event=>{if(root.contains(event.target)&&event.deltaY>0&&atEnd())next();},{passive:true});
  root.addEventListener('touchstart',event=>{const t=event.touches[0];touch={x:t.clientX,y:t.clientY,nav:nav.contains(event.target)};},{passive:true});
  root.addEventListener('touchend',event=>{if(!touch)return;const t=event.changedTouches[0],dx=touch.x-t.clientX,dy=touch.y-t.clientY;if(touch.nav&&Math.abs(dx)>45&&Math.abs(dx)>Math.abs(dy)){next(dx>0?1:-1);}else if(dy>45&&Math.abs(dy)>Math.abs(dx)&&atEnd())next();touch=null;},{passive:true});
  nav.addEventListener('keydown',event=>{if(event.key==='ArrowRight'||event.key==='ArrowLeft'){event.preventDefault();next(event.key==='ArrowRight'?1:-1);categories.find(b=>b.dataset.categoryFilter===active)?.focus();}});
})();
