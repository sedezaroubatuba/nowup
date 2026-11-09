(()=>{'use strict';
 const parse=v=>{try{return JSON.parse(v||'{}');}catch(_){return {};}};
 const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text)n.textContent=text;if(cls)n.className=cls;return n;};
 const money=n=>(Number(n)/100).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
 document.querySelectorAll('[data-fashion-form385]').forEach(form=>{
  const presets=parse(form.querySelector('[data-fashion-presets387]')?.textContent),select=form.querySelector('[name=guide387]'),input=form.querySelector('[name=measurements387]');
  select?.addEventListener('change',()=>{if(input.value.trim()&&!confirm('Substituir as medidas atuais pelo modelo selecionado?'))return;input.value=presets[select.value]?.text||'';});
 });
 if(!document.body.classList.contains('public-profile-area'))return;
 document.body.classList.add('fashion-catalog385');
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
  const choices=panel.querySelector('.nu192-choices');if(choices)panel.querySelector(':scope > h3')?.after(choices);
  const price=panel.querySelector('strong');if(price)choices?.before(price);
  const guide=el('button','📏 Guia de medidas','nu387-guide');guide.type='button';
  if(meta.guide&&meta.guide!=='none'&&meta.measurements){
   guide.onclick=()=>{const d=modal('Guia de medidas'),hint=el('p','Medidas de referência em cm. Podem variar por marca e modelo; confirme com a loja.'),wrap=el('div',null,'nu387-table-wrap'),table=el('table');meta.measurements.split('\n').filter(l=>l.trim()).forEach((line,i)=>{const row=el('tr');line.split(';').forEach(v=>row.append(el(i?'td':'th',v.trim())));table.append(row);});wrap.append(table);d.append(hint,wrap);d.showModal();};(choices||panel).after(guide);if(!choices)panel.append(guide);
  }
  const favorite=el('button','♡ Favoritar','nu387-favorite');favorite.type='button';let saved=[];try{saved=parse(localStorage.getItem('nowup-fashion-favorites387')||'[]');}catch(_){}if(!Array.isArray(saved))saved=[];
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
 document.addEventListener('click',e=>{const item=e.target.closest('[data-source256]');if(!item||!item.classList.contains('nu201-card')||e.target.closest('a'))return;const card=sources.get(item.dataset.source256);if(!card)return;e.preventDefault();e.stopImmediatePropagation();open(card);},true);
 document.addEventListener('click',e=>{const choose=e.target.closest('.nu151-choose');if(choose)decorate(choose.closest('[data-product]'));});
 // Prepare original detail cards, including items with a single size.
 sources.forEach(decorate);
})();
