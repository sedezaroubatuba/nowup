/* Public discovery below the existing store list; purchasing stays in each store. */
(()=>{'use strict';
function start(){
 const slogan=document.querySelector('.v50-home .h210-slogan'),top=document.querySelector('body>.top');if(top&&slogan)top.append(slogan);
 const host=document.querySelector('.nu292-market');if(!host)return;
 const money=new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}),tabs=[...host.querySelectorAll('[data-market-tab]')],panels=[...host.querySelectorAll('[data-market-panel]')];
 const make=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text)n.textContent=text;return n;};
 function select(kind,focus=false){tabs.forEach(t=>{const active=t.dataset.marketTab===kind;t.setAttribute('aria-selected',String(active));t.tabIndex=active?0:-1;if(active&&focus)t.focus();});panels.forEach(p=>p.hidden=p.dataset.marketPanel!==kind);}
 tabs.forEach((tab,i)=>{tab.addEventListener('click',()=>select(tab.dataset.marketTab));tab.addEventListener('keydown',e=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;e.preventDefault();const next=e.key==='Home'?0:e.key==='End'?tabs.length-1:(i+(e.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;select(tabs[next].dataset.marketTab,true);});});
 const city=new URLSearchParams(location.search).get('city')||document.querySelector('input[name="city"]')?.value||'';
 async function load(panel){const kind=panel.dataset.marketPanel,title=panel.querySelector('h2');try{
  const response=await fetch('/api/experimente-hoje?'+new URLSearchParams({city,kind}),{credentials:'same-origin',cache:'no-store'});if(!response.ok)throw Error('feed');const data=await response.json();
  const row=make('div','nu292-products');row.tabIndex=0;row.setAttribute('aria-label',(kind==='combos'?'Combos':'Promoções')+' de várias lojas; deslize para o lado');
  for(const p of (Array.isArray(data.items)?data.items:[]).slice(0,60)){
   let url;try{url=new URL(p.url,location.origin);}catch(_){continue;}if(url.origin!==location.origin||!/^\/p\/[^/]+\/menu$/.test(url.pathname)||!Number.isFinite(p.price_cents)||p.price_cents<=0)continue;
   const card=make('a','nu292-card');card.href=url.pathname+url.search;card.setAttribute('aria-label',p.name+' — '+p.shop+' — '+money.format(p.price_cents/100));
   const image=make('img');image.src='/static/product-placeholder.svg';image.dataset.src258=p.image;image.alt=p.name;image.loading='lazy';image.decoding='async';image.addEventListener('error',()=>{image.src='/static/product-placeholder.svg';},{once:true});
   card.append(image,make('small','nu292-shop',p.shop),make('h3','',p.name));
   if(p.discount_percent>0)card.append(make('span','nu292-badge','−'+p.discount_percent+'%'));
   else if(kind==='combos')card.append(make('span','nu292-badge nu292-combo','COMBO'));
   const price=make('div','nu292-price');price.append(make('small','',kind==='combos'?'Preço do combo':'Preço promocional'));if(p.regular_price_cents>p.price_cents)price.append(make('del','',money.format(p.regular_price_cents/100)));price.append(make('strong','',money.format(p.price_cents/100)));card.append(price,make('span','nu292-view','Ver na loja ›'));
   card.addEventListener('click',()=>{try{sessionStorage.setItem('food91-target',JSON.stringify({id:p.id,name:p.product_name||p.name,path:url.pathname}));}catch(_){}});row.append(card);
  }
  panel.replaceChildren(title);if(row.children.length){panel.append(row,make('small','nu292-hint','Deslize para conhecer ofertas de outras lojas'));}else panel.append(make('p','nu292-empty',kind==='combos'?'Os combos das lojas abertas aparecerão aqui.':'As promoções das lojas abertas aparecerão aqui.'));
 }catch(_){panel.querySelector('[role=status]').textContent='Não foi possível carregar agora. Atualize a página para tentar novamente.';}}
 panels.forEach(load);
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();})();
