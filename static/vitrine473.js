(() => {
  const root = document.querySelector('[data-vitrine]');
  if (!root) return;
  const customer = Number(root.dataset.customer);
  const status = root.querySelector('[data-vitrine-status]');
  const slugPattern = /^[a-zA-Z0-9_-]+$/;
  const storage = customer ? localStorage : sessionStorage;
  const cartKey = slug => 'nowup-cart:' + (customer ? 'u:' + customer + ':' : '') + '/p/' + slug;
  const menuUrl = slug => '/p/' + slug + '/menu';
  const entries = slug => new Map(JSON.parse(storage.getItem(cartKey(slug)) || '[]'));

  function refresh() {
    root.querySelectorAll('[data-vitrine-item]').forEach(button => {
      const item=JSON.parse(button.dataset.vitrineItem);
      const parent=button.parentElement;
      let step=parent.querySelector('.vitrine-step493');
      if(!step){
        step=document.createElement('div');step.className='vitrine-step493';
        const minus=document.createElement('button'), count=document.createElement('span'), plus=document.createElement('button');
        minus.type=plus.type='button';minus.textContent='−';plus.textContent='+';
        minus.setAttribute('aria-label','Diminuir '+item.name);plus.setAttribute('aria-label','Aumentar '+item.name);
        count.setAttribute('aria-live','polite');minus.onclick=()=>add(item,-1,parent.closest(".nu512-horizontal,.vitrine-product-card")||parent);plus.onclick=()=>add(item,1,parent.closest(".nu512-horizontal,.vitrine-product-card")||parent);
        step.append(minus,count,plus);parent.append(step);
      }
      let quantity=0;
      try{quantity=Number(entries(item.slug).get(item.id+'::utensils0:notes')?.quantity||0);}catch(_){}
      const active=!item.options&&quantity>0;
      button.hidden=active;step.hidden=!active;
      step.querySelector('span').textContent=String(quantity);
      step.lastElementChild.disabled=button.disabled||quantity>=Math.max(1,Math.min(99,Number(item.max)||99));
    });
    let total=0;
    document.querySelectorAll('[data-vitrine-cart]').forEach(link => {
      let count = 0;
      try { count = [...entries(link.dataset.slug).values()].reduce((n, row) => n + Number(row.quantity || 0), 0); } catch (_) {}
      total += count;
      link.hidden = count < 1;
      link.querySelector('[data-vitrine-count]').textContent = String(count);
      link.setAttribute('aria-label', 'Carrinho '+(link.querySelector('.nu510-cart-name')?.textContent||'')+', ' + count + (count === 1 ? ' item' : ' itens'));
    });
    const summary=document.querySelector('[data-nu510-total]'); if(summary) summary.textContent=String(total);
    const empty=document.querySelector('.nu510-cart-empty'); if(empty) empty.hidden=total>0;
  }

  function add(item, delta=1, source=null) {
    if (!item || !slugPattern.test(item.slug) || !Number.isSafeInteger(item.id) || item.id < 1) return;
    if (item.options) {
      location.assign(menuUrl(item.slug) + '?produto=' + item.id + '&vitrine_opcoes=1');
      return;
    }
    try {
      const cart = entries(item.slug);
      const id = item.id + '::utensils0:notes';
      const max = Math.max(1, Math.min(99, Number(item.max) || 99));
      const quantity = Number(cart.get(id)?.quantity || 0);
      if (delta>0 && quantity >= max) {
        status.dataset.error='1';status.textContent = 'Limite de unidades deste produto atingido.';
        return;
      }
      if(quantity+delta<=0)cart.delete(id);
      else cart.set(id, {productId:item.id, name:item.name, unitPrice:item.price, quantity:quantity+delta,
        notes:'', options:[], utensils:false, max});
      storage.setItem(cartKey(item.slug), JSON.stringify([...cart]));
      if (customer) localStorage.setItem('nowup-cart-info:u:' + customer + ':/p/' + item.slug,
        JSON.stringify({name:item.store, updated:Date.now()}));
      delete status.dataset.error;status.textContent = delta>0 ? item.name + ' adicionado ao carrinho.' : 'Quantidade atualizada.';
      refresh();
      window.dispatchEvent(new Event('nowup-cart-changed'));
      if(delta>0) window.NOWUP_CART_BAG366?.added(source);
    } catch (_) {
      status.dataset.error='1';status.textContent = 'Não foi possível atualizar o carrinho. Tente novamente.';
    }
  }

  window.NowUpVitrine473 = {add};
  root.addEventListener('click', event => {
    const button = event.target.closest('[data-vitrine-item]');
    if (button) add(JSON.parse(button.dataset.vitrineItem),1,button.closest(".nu512-horizontal,.vitrine-product-card")||button.parentElement);
  });

  const filter=root.querySelector('#nu512-store-filter');
  const openFilter=root.querySelector('[data-nu512-filter]');
  if(filter&&openFilter){
    openFilter.addEventListener('click',()=>{
      if(typeof filter.showModal==='function')filter.showModal();
      else location.assign('/lojas?city='+encodeURIComponent(filter.querySelector('[name=city]')?.value||''));
    });
    filter.querySelector('[data-nu512-close]')?.addEventListener('click',()=>filter.close());
    filter.addEventListener('click',event=>{if(event.target===filter)filter.close();});
    const query=filter.querySelector('[data-nu512-shop-search]');
    query?.addEventListener('input',()=>{
      const normalize=value=>String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
      const term=normalize(query.value.trim());
      filter.querySelectorAll('[data-shop-name]').forEach(row=>{row.hidden=!!term&&!normalize(row.dataset.shopName).includes(term);});
    });
  }
  window.addEventListener('pageshow', refresh);
  window.addEventListener('storage', refresh);
  refresh();
  root.querySelectorAll('.nu510-expand').forEach(button=>{
    button.addEventListener('click',()=>{
      const shelf=button.closest('.vitrine-shelf'), open=button.getAttribute('aria-expanded')!=='true';
      button.setAttribute('aria-expanded',String(open));button.textContent=open?'Ver menos ‹':'Ver todos ›';
      shelf.classList.toggle('nu510-expanded',open);
      if(!open){shelf.querySelector('.vitrine-products')?.scrollTo({left:0});shelf.scrollIntoView({block:'start',behavior:'smooth'});}
    });
  });
  root.querySelectorAll('[data-nu494-scroll]').forEach(track=>{
    const dots=track.nextElementSibling;
    if(!dots?.classList.contains('nu494-dots'))return;
    const size=Number(track.dataset.pageSize)||4;
    const pages=Math.ceil(track.children.length/size);
    if(pages<2){dots.hidden=true;return;}
    const buttons=Array.from({length:pages},(_,i)=>{
      const button=document.createElement('button');button.type='button';
      button.setAttribute('aria-label','Página '+(i+1));
      button.onclick=()=>{track.dispatchEvent(new Event('nu501-manual'));track.scrollTo({left:track.children[Math.min(i*size,track.children.length-1)].offsetLeft-track.children[0].offsetLeft,behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});};
      dots.append(button);return button;
    });
    const update=()=>{
      const max=track.scrollWidth-track.clientWidth;
      const index=max<=0?0:Math.round((track.scrollLeft/max)*(pages-1));
      buttons.forEach((b,i)=>b.setAttribute('aria-current',String(i===index)));
    };
    track.addEventListener('scroll',update,{passive:true});update();
    if(size===1&&track.matches('.nu494-hero-track')){
      window.NowUpAutoSlide501?.attach({track,controls:track,advance:()=>{
        const children=[...track.children],max=Math.max(0,track.scrollWidth-track.clientWidth);
        const left=i=>Math.min(max,Math.max(0,children[i].offsetLeft-children[0].offsetLeft));
        const current=track.scrollLeft>=max-2?children.length-1:children.reduce((best,_,i)=>Math.abs(track.scrollLeft-left(i))<Math.abs(track.scrollLeft-left(best))?i:best,0);
        const next=(current+1)%children.length;
        track.scrollTo({left:left(next),behavior:next===0?'instant':'smooth'});
      }});
    }
  });
})();
