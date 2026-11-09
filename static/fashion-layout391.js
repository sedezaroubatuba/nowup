/* One compact renderer for fashion home, categories and search. */
window.NOWUP_FASHION_LAYOUT391=({root,originals,compact,sticky,nav,intro,showcase,categoryView,layout,back,cartRefreshers,search})=>{
 const body=document.body;body.classList.remove('nu187-store-home','nu191-category');body.classList.add('nu391-fashion');
 intro.hidden=showcase.hidden=categoryView.hidden=true;layout.hidden=true;back.hidden=true;if(nav)sticky.append(nav);
 const grid=document.createElement('main');grid.className='nu391-fashion-grid';grid.setAttribute('aria-label','Peças da loja');layout.before(grid);
 const empty=document.createElement('p');empty.className='nu391-empty';empty.textContent='Nenhuma peça encontrada.';empty.hidden=true;grid.after(empty);
 const cards=originals.map((source,index)=>{const node=compact(source);node.classList.add('nu391-fashion-card');for(const [key,value] of Object.entries({height:'auto','min-height':'0','max-height':'none',padding:'0','align-self':'start'}))node.style.setProperty(key,value,'important');const photo=node.querySelector(':scope > img');if(photo)for(const [key,value] of Object.entries({width:'100%',height:'auto','min-height':'0','max-height':'none','object-fit':'contain','aspect-ratio':'var(--nu391-photo-ratio)'}))photo.style.setProperty(key,value,'important');node.style.setProperty('--nu391-photo-ratio',index%4===0?'0.68':index%4===1?'1.15':index%4===2?'0.90':'0.75');grid.append(node);return {source,node};});
 let category='all',frame=0;
 const normalize=v=>String(v||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
 function measure(){frame=0;cards.forEach(({node})=>{if(!node.hidden)node.style.gridRowEnd='span '+Math.ceil((node.getBoundingClientRect().height+12)/4);});}
 function schedule(){if(!frame)frame=requestAnimationFrame(measure);}
 function filter(){const q=normalize(search.value.trim());let count=0;cards.forEach(({source,node})=>{node.hidden=(category!=='all'&&source.dataset.category!==category)||!normalize(source.dataset.name+' '+(source.querySelector('.menu-product-info p')?.textContent||'')).includes(q);node.style.setProperty('display',node.hidden?'none':'flex','important');if(!node.hidden){node.classList.toggle('nu391-featured',count===0);node.style.setProperty('--nu391-photo-ratio',count%4===0?'0.68':count%4===1?'1.15':count%4===2?'0.90':'0.75');count++;}});empty.hidden=count>0;nav?.querySelectorAll('[data-category-filter]').forEach(b=>{const active=b.dataset.categoryFilter===category;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active));b.style.setProperty('background',active?'#7132bf':'#f7f5fa','important');b.style.setProperty('color',active?'#fff':'#4d286d','important');});schedule();}
 root.addEventListener('click',e=>{const b=e.target.closest('[data-category-filter]');if(!b)return;e.preventDefault();e.stopImmediatePropagation();category=b.dataset.categoryFilter;filter();b.scrollIntoView({block:'nearest',inline:'nearest'});grid.scrollIntoView({block:'start',behavior:'auto'});},true);
 root.addEventListener('input',e=>{if(e.target!==search)return;e.stopImmediatePropagation();filter();},true);
 root.addEventListener('search',e=>{if(e.target!==search)return;e.stopImmediatePropagation();filter();},true);
 window.addEventListener('nowup-cart-changed',()=>{cartRefreshers.forEach(fn=>fn());schedule();});
 if(typeof ResizeObserver!=='undefined'){const observer=new ResizeObserver(schedule);cards.forEach(({node})=>observer.observe(node));}
 grid.addEventListener('load',schedule,true);window.addEventListener('resize',schedule);filter();window.NOWUP_FASHION_REMOVE391?.();body.dataset.store187Ready='1';
};
