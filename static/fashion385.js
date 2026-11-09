(()=>{'use strict';
 const parse=v=>{try{return JSON.parse(v||'{}');}catch(_){return {};}};
 const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text)n.textContent=text;if(cls)n.className=cls;return n;};
 const money=n=>(Number(n)/100).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
 document.querySelectorAll('[data-fashion-form385]').forEach(form=>{
  const presets=parse(form.querySelector('[data-fashion-presets387]')?.textContent),select=form.querySelector('[name=guide387]'),input=form.querySelector('[name=measurements387]');
  select?.addEventListener('change',()=>{if(input.value.trim()&&!confirm('Substituir as medidas atuais pelo modelo selecionado?'))return;input.value=presets[select.value]?.text||'';});
 });
 document.querySelectorAll('[data-fashion-form385]').forEach(form=>{
  const mode=form.querySelector('[name=stock_mode389]'),total=form.querySelector('[data-stock-total389]'),sizes=form.querySelector('[data-stock-sizes389]'),raw=form.querySelector('[name=stock_sizes389]'),list=form.querySelector('[name=sizes385]');if(!mode)return;
  const grid=el('div',null,'nu389-stock-editor');raw.after(grid);raw.hidden=true;raw.style.setProperty('display','none','important');
  function rebuild(){const counts=new Map(raw.value.split('\n').map(l=>l.split(';').map(s=>s.trim())));grid.replaceChildren();const names=list.value.replaceAll(';',',').split(',').map(s=>s.trim()).filter(Boolean);for(const name of names){const label=el('label',name),i=el('input');i.type='number';i.min='0';i.max='99999';i.value=counts.get(name)||'0';i.setAttribute('aria-label','Estoque '+name);i.dataset.stockSize389=name;label.append(i);grid.append(label);}if(!names.length)grid.append(el('small','Informe os tamanhos disponíveis acima.'));}
  function serialize(){raw.value=[...grid.querySelectorAll('input')].map(i=>i.dataset.stockSize389+';'+i.value).join('\n');}
  grid.addEventListener('input',serialize);list.addEventListener('change',()=>{const names=list.value.replaceAll(';',',').split(',').map(s=>s.trim()).filter(Boolean);if(JSON.stringify(names)===JSON.stringify([...grid.querySelectorAll('input')].map(i=>i.dataset.stockSize389)))return;serialize();rebuild();});mode.addEventListener('change',sync);function sync(){total.hidden=mode.value!=='total';sizes.hidden=mode.value!=='sizes';const variants=form.querySelector('[data-stock-variants391]');if(variants)variants.hidden=mode.value!=='variants';total.querySelector('input').required=mode.value==='total';}rebuild();sync();form.addEventListener('submit',serialize);
 });
 if(!document.body.classList.contains('public-profile-area'))return;
 document.body.classList.add('fashion-catalog385');
 window.NOWUP_FASHION389={validate(card,configs,replaceId){const stock=parse(card.dataset.fashionDetails387).stock||{};if(!stock.mode||stock.mode==='none')return;const existing=(window.NOWUP_CART160.entries389?.()||[]).filter(v=>v.id!==replaceId&&Number(v.productId)===Number(card.dataset.id)),counts={};const key=c=>stock.mode==='sizes'?(c.customization?.groups?.fashionSize385?.[0]||''):'';existing.forEach(c=>counts[key(c)]=(counts[key(c)]||0)+c.quantity);configs.forEach(c=>counts[key(c)]=(counts[key(c)]||0)+1);for(const [size,n] of Object.entries(counts)){const limit=stock.mode==='sizes'?(stock.sizes?.[size]||0):stock.total;if(stock.mode==='variants')continue;if(n>limit)throw new Error('Quantidade maior que o estoque informado'+(size?' para '+size:'')+'.');}}};
 const sources=new Map([...document.querySelectorAll('[data-product]')].map(c=>[c.dataset.id,c]));
 const imageURL=c=>{const i=c.querySelector(':scope > img');return c.dataset.fashionPrimary387||i?.dataset.src258||i?.src||i?.currentSrc;};
 function modal(title){const d=el('dialog',null,'nu387-info-dialog'),header=el('header'),h=el('h2',title),close=el('button','×');close.type='button';close.setAttribute('aria-label','Fechar');close.onclick=()=>d.close();header.append(h,close);d.append(header);d.addEventListener('close',()=>d.remove());document.body.append(d);return d;}
 function open(card){const current=document.querySelector('.nu151-dish-dialog[open]');if(current){current.querySelector('[data-close160]')?.click();setTimeout(()=>open(card),0);return;}card.querySelector('.nu151-choose')?.click();decorate(card);}
 function decorate(card){
  if(!card||card.querySelector('.nu385-gallery'))return;
  const panel=card.querySelector('.menu-product-info');if(!panel)return;
  const meta=parse(card.dataset.fashionDetails387),first=imageURL(card);let files=parse(card.dataset.fashionPhotos385||'[]');if(!Array.isArray(files))files=[];
  const urls=[...(first?[first]:[]),...files.filter(f=>typeof f==='string'&&/^[a-zA-Z0-9_.-]+$/.test(f)).slice(0,4).map(f=>'/uploads/'+encodeURIComponent(f))];
  const gallery=el('div',null,'nu385-gallery'),photoButton=el('button',null,'nu385-photo'),photo=el('img');photoButton.type='button';photoButton.setAttribute('aria-label','Ampliar foto de '+card.dataset.name);photo.src=urls[0]||'/static/product-placeholder.svg';photo.alt=card.dataset.name;photo.loading='lazy';photoButton.append(photo);
  photoButton.onclick=()=>{const d=modal('Foto ampliada');d.classList.add('nu387-zoom');const img=el('img');img.src=photo.src;img.alt=photo.alt;d.append(img);d.showModal();};
  const thumbs=el('div',null,'nu385-thumbs');urls.forEach((url,i)=>{const b=el('button'),img=el('img');b.type='button';b.setAttribute('aria-label','Ver foto '+(i+1));img.src=url;img.alt='';img.loading='lazy';b.append(img);b.onclick=()=>photo.src=url;thumbs.append(b);});gallery.append(photoButton,thumbs);panel.prepend(gallery);
  const description=panel.querySelector(':scope > p');if(description)description.classList.add('nu387-original-description');
  const choices=panel.querySelector('.nu192-choices');
  const palette={preto:'#202024',branco:'#fff',roxo:'#7132bf',azul:'#2589df',rosa:'#e57da8',rose:'#c98899',vermelho:'#d43c41',verde:'#4d8964',bege:'#d4bea0',marrom:'#81583e',cinza:'#999',amarelo:'#edc64b',laranja:'#ed8b3e'};
  card.querySelectorAll('[data-group192="fashionColor385"]').forEach(i=>{const label=i.closest('label'),name=i.value.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');label.classList.add('nu389-color');const swatch=el('i');swatch.setAttribute('aria-hidden','true');swatch.style.background=palette[name]||'linear-gradient(135deg,#b698d1,#5bb8cb)';label.querySelector('span')?.prepend(swatch);});
  if(choices)panel.querySelector(':scope > h3')?.after(choices);
  const price=panel.querySelector('strong');if(price)choices?.before(price);
  const guide=el('button','📏 Guia de medidas','nu387-guide');guide.type='button';
  if(meta.guide&&meta.guide!=='none'&&meta.measurements){
   guide.onclick=()=>{const d=modal('Guia de medidas'),hint=el('p','Medidas de referência em cm. Podem variar por marca e modelo; confirme com a loja.'),wrap=el('div',null,'nu387-table-wrap'),table=el('table');meta.measurements.split('\n').filter(l=>l.trim()).forEach((line,i)=>{const row=el('tr');line.split(';').forEach(v=>row.append(el(i?'td':'th',v.trim())));table.append(row);});wrap.append(table);d.append(hint,wrap);d.showModal();};(choices||panel).after(guide);if(!choices)panel.append(guide);
  }
  const quantity=el('section',null,'nu389-quantity'),heading=el('b','Quantidade'),controls=el('div'),minus=el('button','−'),input=el('input'),plus=el('button','+'),balance=el('small',null,'nu389-balance');minus.type=plus.type='button';minus.setAttribute('aria-label','Diminuir quantidade');plus.setAttribute('aria-label','Aumentar quantidade');input.type='number';input.min='1';input.max=card.dataset.max||'99';input.value='1';input.inputMode='numeric';input.dataset.fashionQuantity389='';input.setAttribute('aria-label','Quantidade desejada');controls.append(minus,input,plus);quantity.append(heading,controls,balance);panel.querySelector('.product-buy')?.before(quantity);
  const stock=meta.stock||{mode:'none'};
  function refreshStock(){const selected=card.querySelector('[data-group192="fashionSize385"]:checked')?.value,limit=stock.mode==='sizes'?(selected?(stock.sizes?.[selected]||0):null):stock.mode==='total'?stock.total:null;balance.textContent=stock.mode==='none'?'':limit===null?'Escolha o tamanho para ver a disponibilidade.':limit+' '+(limit===1?'unidade disponível':'unidades disponíveis')+(selected?' no tamanho '+selected:'');input.max=String(Math.min(Number(card.dataset.max)||99,limit===null?99:limit));minus.disabled=Number(input.value)<=1;plus.disabled=Number(input.value)>=Number(input.max);}
  for(const button of [minus,plus])button.onclick=()=>{const next=Number(input.value)+(button===plus?1:-1);if(next<1||next>Number(input.max))return;input.value=String(next);input.dispatchEvent(new Event('input',{bubbles:true}));};input.addEventListener('input',refreshStock);card.addEventListener('change',refreshStock);if(stock.mode==='sizes')card.querySelectorAll('[data-group192="fashionSize385"]').forEach(i=>{if(!stock.sizes?.[i.value]){i.disabled=true;i.closest('label').title='Tamanho esgotado';}});refreshStock();
  const favorite=el('button' ,'♡ Favoritar','nu387-favorite');favorite.type='button';let saved=[];try{saved=parse(localStorage.getItem('nowup-fashion-favorites387')||'[]');}catch(_){}if(!Array.isArray(saved))saved=[];
  const favkey=location.pathname+':'+card.dataset.id;let liked=saved.includes(favkey);const paint=()=>{favorite.textContent=liked?'♥ Favoritado':'♡ Favoritar';favorite.setAttribute('aria-pressed',String(liked));};paint();favorite.onclick=()=>{liked=!liked;try{let all=parse(localStorage.getItem('nowup-fashion-favorites387')||'[]');if(!Array.isArray(all))all=[];localStorage.setItem('nowup-fashion-favorites387',JSON.stringify(liked?[...new Set([...all,favkey])]:all.filter(x=>x!==favkey)));}catch(_){}paint();};panel.querySelector('.product-buy')?.after(favorite);
  const details=el('section',null,'nu387-details');details.append(el('h3','Descrição'),el('p',description?.textContent||'Consulte a loja para mais informações.'));
  const entries=[['Marca',meta.brand],['Material',meta.material],['Composição',meta.composition]].filter(x=>x[1]);if(entries.length){details.append(el('h3','Detalhes do produto'));const dl=el('dl');entries.forEach(([k,v])=>dl.append(el('dt',k),el('dd',v)));details.append(dl);}
  panel.append(details);
  const related=(card.dataset.related256||'').split(',').map(id=>sources.get(id.trim())).filter(c=>c&&c!==card&&c.dataset.available256!=='0').slice(0,5);
  if(related.length){const box=el('section',null,'nu387-related'),grid=el('div',null,'nu387-related-grid');box.append(el('h3','Combine com esta peça'),grid);related.forEach(c=>{const b=el('button',null,'nu387-related-card');b.type='button';const img=el('img');img.src=imageURL(c)||'/static/product-placeholder.svg';img.alt=c.dataset.name;img.loading='lazy';b.append(img,el('b',c.dataset.name),el('span',money(c.dataset.price)),el('small','Ver peça'));b.onclick=()=>open(c);grid.append(b);});panel.append(box);}
  panel.append(el('p','Retirada ou entrega a combinar pelo WhatsApp.','nu387-delivery'));
  const note=panel.querySelector('.nu85-note');if(note){const input=note.querySelector('textarea');if(input)input.placeholder='Ex.: preferência de cor ou dúvidas sobre a peça';note.querySelector('small')?.remove();}
 }
 // Open the original product node: its size choices and server-validated cart stay intact.
 document.addEventListener('click',e=>{const item=e.target.closest('[data-source256]');if(!item||!item.classList.contains('nu201-card')||e.target.closest('a,.nu-step263,[data-fashion-remove391]'))return;const card=sources.get(item.dataset.source256);if(!card)return;e.preventDefault();e.stopImmediatePropagation();open(card);},true);
 document.addEventListener('click',e=>{const choose=e.target.closest('.nu151-choose');if(choose)decorate(choose.closest('[data-product]'));});
 // The common compact card owns quantity; do not intercept its +/- controls.
 function removeButtons391(){document.querySelectorAll('.nu201-card.nu-cart-in262').forEach(card=>{if(card.querySelector('[data-fashion-remove391]'))return;const b=el('button','Remover','nu391-remove');b.type='button';b.dataset.fashionRemove391='';b.setAttribute('aria-label','Remover todas as unidades de '+(sources.get(card.dataset.source256)?.dataset.name||'peça'));b.onclick=()=>window.NOWUP_CART160?.removeProduct(card.dataset.source256);card.querySelector('.nu-cart-actions262')?.append(b);});document.querySelectorAll('.nu201-card:not(.nu-cart-in262) [data-fashion-remove391]').forEach(b=>b.remove());}
 window.NOWUP_FASHION_REMOVE391=removeButtons391;
 window.addEventListener('nowup-cart-changed',()=>queueMicrotask(removeButtons391));
 // Prepare original detail cards, including items with a single size.
 sources.forEach(decorate);
})();
