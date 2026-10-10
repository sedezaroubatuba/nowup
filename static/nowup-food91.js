(() => {
  'use strict';
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };
  const money = new Intl.NumberFormat('pt-BR', {style:'currency', currency:'BRL'});
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let loading = false, updated = 0;
  async function load() {
    if (loading) return; loading = true;
    try {
      const city = new URLSearchParams(location.search).get('city') || document.querySelector('input[name="city"]')?.value || '';
      const response = await fetch('/api/experimente-hoje?city=' + encodeURIComponent(city), {credentials:'same-origin',cache:'no-store'});
      if (!response.ok) throw new Error('feed');
      const data = await response.json();
      document.getElementById('food91')?.remove();
      if (!data.items.length) { updated = Date.now(); return; }
      const section = el('section'); section.id = 'food91'; section.setAttribute('aria-label','Experimente hoje');
      section.append(el('h2', '', 'Experimente hoje'), el('p','food91-hint','Deslize para ver mais opções →'));
      const track = el('div','food91-track'); track.tabIndex = 0; track.setAttribute('aria-label','Produtos em páginas de seis');
      const pages = [];
      for(let i=0;i<data.items.length;i+=6){
        const page=el('div','food91-page');
        for(const p of data.items.slice(i,i+6)){
          const card=el('article','food91-card'), img=el('img','food91-photo'); img.src=p.image; img.alt=p.name; img.loading='lazy'; img.decoding='async';
          img.addEventListener('error',()=>{img.removeAttribute('src');img.alt='Foto indisponível';},{once:true});
          const copy=el('div','food91-copy');
          const link=el('a','food91-link','Ver produto'); link.href=p.url; link.setAttribute('aria-label','Ver '+p.name+' em '+p.shop);
          link.addEventListener('click',()=>{try{sessionStorage.setItem('food91-target',JSON.stringify({id:p.id,name:p.product_name,path:new URL(p.url,location.origin).pathname}));}catch(_){}});
          copy.append(el('h3','',p.name),el('p','food91-price',money.format(p.price_cents/100)),el('p','food91-shop',p.shop),link);card.append(img,copy);page.append(card);
        } track.append(page);pages.push(page);
      }
      section.append(track);
      const controls=el('div','food91-controls'), prev=el('button','','‹'), next=el('button','','›'), dots=el('div','food91-dots'), count=el('p','food91-count');
      prev.type=next.type='button';prev.setAttribute('aria-label','Página anterior');next.setAttribute('aria-label','Próxima página');count.setAttribute('aria-live','polite');
      let current=0;
      function sync(){ current=pages.reduce((best,p,i)=>Math.abs(p.offsetLeft-pages[0].offsetLeft-track.scrollLeft)<Math.abs(pages[best].offsetLeft-pages[0].offsetLeft-track.scrollLeft)?i:best,0);prev.disabled=current===0;next.disabled=current===pages.length-1;count.textContent=(current+1)+' de '+pages.length;dots.replaceChildren();for(let i=Math.max(0,current-2);i<Math.min(pages.length,Math.max(5,current+3));i++){const d=el('span','food91-dot'+(i===current?' active':''));dots.append(d);}}
      function go(delta){const i=Math.max(0,Math.min(pages.length-1,current+delta));track.scrollTo({left:pages[i].offsetLeft-pages[0].offsetLeft,behavior:reduced?'auto':'smooth'});}
      prev.onclick=()=>go(-1);next.onclick=()=>go(1);track.addEventListener('keydown',e=>{if(e.target!==track)return;if(e.key==='ArrowRight'||e.key==='ArrowLeft'){e.preventDefault();go(e.key==='ArrowRight'?1:-1);}});
      track.addEventListener('scroll',sync,{passive:true});controls.append(prev,dots,next);if(pages.length>1)section.append(controls,count);
      const main=document.querySelector('main.v50-home')||document.querySelector('main');
      const footer=document.querySelector('footer');
      if(footer && (!main||main.contains(footer)))footer.before(section);else if(main)main.append(section);else if(footer)footer.before(section);else return;
      requestAnimationFrame(sync);updated=Date.now();
    } catch(error) { console.warn('NowUp: vitrine de refeições indisponível.'); }
    finally {loading=false;}
  }
  function focusProduct(){
    const id=new URLSearchParams(location.search).get('produto');if(!id||!/^\d+$/.test(id))return;
    let target;try{target=JSON.parse(sessionStorage.getItem('food91-target')||'null');}catch(_){}
    let node=document.getElementById('produto-'+id)||document.getElementById('product-'+id)||document.querySelector('[data-product-id="'+id+'"]');
    if(!node&&target?.path===location.pathname&&String(target.id)===id){const title=[...document.querySelectorAll('h2,h3,h4')].find(n=>n.textContent.trim()===target.name);node=title?.closest('article')||title;}
    if(node){node.classList.add('food91-highlight');node.scrollIntoView({block:'center',behavior:reduced?'auto':'smooth'});}
  }
  if(location.pathname==='/'){load();setInterval(()=>{if(!document.hidden)load();},300000);document.addEventListener('visibilitychange',()=>{if(!document.hidden&&Date.now()-updated>60000)load();});}else if(/^\/p\/[^/]+\/menu\/?$/.test(location.pathname)){focusProduct();}
})();
