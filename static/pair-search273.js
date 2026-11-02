/* Independent search in every product form; filtered selections remain submitted. */
(()=>{
 'use strict';
 const normalize=value=>String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim();
 function hydrate328(picker){
  if(picker.dataset.ready328)return;picker.dataset.ready328='1';
  let catalog=[];try{catalog=JSON.parse(document.getElementById('pair-catalog328')?.textContent||'[]');}catch(_){}
  if(!document.getElementById('pair-catalog328'))return;
  const selected=new Set((picker.dataset.selected328||'').split(',')),box=picker.querySelector('.nu273-options');
  const own=picker.closest('[data-product-id]')?.dataset.productId;
  box.replaceChildren();const fragment=document.createDocumentFragment();
  for(const product of catalog){if(String(product.id)===own)continue;
   const label=document.createElement('label'),input=document.createElement('input'),name=document.createElement('span');label.className='check';label.dataset.pairOption273='';input.type='checkbox';input.name='related256';input.value=product.id;input.checked=selected.has(String(product.id));name.textContent=product.name;label.append(input,name);fragment.append(label);
  }box.append(fragment);
 }
 function refresh(picker){
  hydrate328(picker);
  const query=normalize(picker.querySelector('[data-pair-search273]').value);
  const rows=[...picker.querySelectorAll('[data-pair-option273]')];let visible=0,selected=0;
  rows.forEach(row=>{const match=normalize(row.querySelector('span').textContent).includes(query);row.hidden=!match;if(match)visible++;if(row.querySelector('input').checked)selected++;});
  picker.querySelector('[data-pair-status273]').textContent=(visible?visible+' produto(s) encontrado(s)':'Nenhum produto encontrado')+' · '+selected+' selecionado(s)';
 }
 document.addEventListener('input',e=>{if(e.target.matches('[data-pair-search273]'))refresh(e.target.closest('[data-pair-picker273]'));});
 document.addEventListener('change',e=>{const picker=e.target.closest('[data-pair-picker273]');if(picker)refresh(picker);});
 const start=()=>document.querySelectorAll('[data-pair-picker273]').forEach(p=>{if(p.tagName!=='DETAILS'||p.open)refresh(p);});
 document.addEventListener('toggle',event=>{if(event.target.matches?.('[data-pair-picker273]')&&event.target.open)refresh(event.target);},true);
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();
