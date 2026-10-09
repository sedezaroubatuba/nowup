(() => {
  let pending;
  const shuffle = nodes => {
    const a = Array.from(nodes);
    for (let i=a.length-1;i>0;i--) {
      const random = new Uint32Array(1); crypto.getRandomValues(random);
      const j = Math.floor(random[0]/4294967296*(i+1));
      [a[i],a[j]]=[a[j],a[i]];
    }
    return a;
  };
  function setup() {
    const root=document.querySelector('[data-home-discovery]'); if (!root) return;
    const grid=root.querySelector('[data-business-grid]');
    const cards=Array.from(grid.querySelectorAll('.v50-card'));
    cards.forEach((card,i)=>card.hidden=i>=12);
    const carousel=root.querySelector('[data-shop-carousel]');
    shuffle(cards.slice(12).length ? cards.slice(12) : cards).forEach(card=>{const copy=card.cloneNode(true);copy.hidden=false;carousel.append(copy)});
    root.querySelector('[data-shop-carousel-section]').hidden=!cards.length;
    const menus=root.querySelector('[data-menu-carousel]'); shuffle(menus.children).forEach(n=>menus.append(n));
    root.querySelectorAll('[data-show-all]').forEach(button=>{
      button.hidden=cards.length<=12;
      button.addEventListener('click',()=>{
        const expand=button.getAttribute('aria-expanded')!=='true';
        cards.forEach((c,i)=>c.hidden=!expand&&i>=12);
        root.querySelectorAll('[data-show-all]').forEach(b=>{b.setAttribute('aria-expanded',String(expand));b.textContent=expand?'Mostrar menos':`Ver todas as lojas · ${cards.length}`});
        root.querySelector('.v50-search input[name=q]').focus({preventScroll:true});
        grid.scrollIntoView({behavior:'smooth',block:'start'});
      });
    });
    root.querySelectorAll('[data-carousel-next]').forEach(button=>button.addEventListener('click',()=>button.closest('section').querySelector('.discovery-row').scrollBy({left:300,behavior:'smooth'})));
  }
  async function filter(url, push=true) {
    pending?.abort(); const controller=new AbortController();pending=controller;
    const root=document.querySelector('[data-home-discovery]');
    const status=root.querySelector('[data-discovery-status]');status.textContent='Buscando lojas…';root.setAttribute('aria-busy','true');
    try {
      const response=await fetch(url,{credentials:'same-origin',signal:controller.signal});
      if (!response.ok) throw new Error('Busca indisponível');
      const doc=new DOMParser().parseFromString(await response.text(),'text/html');
      const next=doc.querySelector('[data-home-discovery]');if(!next) throw new Error('Página inválida');
      root.replaceWith(next);setup();if(push)history.pushState({},'',url);
      next.querySelector('[data-discovery-status]').textContent='Busca atualizada.';
    } catch (e) { if(e.name!=='AbortError')status.textContent='Não foi possível buscar. Tente novamente.'; }
    finally {root.removeAttribute('aria-busy')}
  }
  document.addEventListener('submit',event=>{
    const form=event.target;
    if(!form.matches('[data-home-discovery] .v50-search, [data-home-discovery] .v50-filter form'))return;
    event.preventDefault(); const url=new URL('/',location.origin);url.search=new URLSearchParams(new FormData(form)).toString();filter(url);
  });
  document.addEventListener('change',event=>{
    if(event.target.matches('[data-home-discovery] .v50-filter select'))event.target.form.requestSubmit();
  });
  document.addEventListener('click',event=>{
    const link=event.target.closest('a');if(!link||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey||event.button!==0)return;
    if(link.matches('[data-home-discovery] .v50-categories a')){event.preventDefault();filter(new URL(link.href));return;}
    // The fixed Explore tab opens the search on this screen.
    if(document.querySelector('[data-home-discovery]')&&link.origin===location.origin&&link.pathname==='/profissionais'){
      event.preventDefault();const search=document.querySelector('.v50-search');search.scrollIntoView({behavior:'smooth'});search.querySelector('input[name=q]').focus({preventScroll:true});
    }
  });
  window.addEventListener('popstate',()=>{if(location.pathname==='/')filter(new URL(location.href),false)});
  setup();
})();
