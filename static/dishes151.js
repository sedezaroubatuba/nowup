(() => {
 'use strict';
 document.querySelectorAll('[data-extras-mode155]').forEach(mode=>{const picker=mode.form?.querySelector('[data-shared-picker155]');const sync=()=>{if(picker){picker.hidden=mode.value!=='selected';picker.style.setProperty('display',mode.value==='selected'?'block':'none','important');}};mode.addEventListener('change',sync);sync();});
 const root=document.querySelector('[data-native-menu]');if(!root)return;
 const cards=[...root.querySelectorAll('[data-product][data-dish="1"]')];if(!cards.length)return;
 const dialog=document.createElement('dialog');dialog.className='nu151-dish-dialog';dialog.setAttribute('aria-label','Personalizar lanche');
 const header=document.createElement('div');header.className='nu160-header';header.innerHTML='<button type="button" data-close160 aria-label="Voltar ao cardápio">←</button><b data-step160>Personalizar</b><label data-amount-label160>Lanches <input type="number" min="1" step="1" value="1" data-amount160 aria-label="Quantidade de lanches"></label>';
 dialog.append(header);root.append(dialog);
 const countInput=header.querySelector('[data-amount160]'),title=header.querySelector('[data-step160]');
 let current=null,marker=null,oldScroll=0,total=1,index=0,drafts=[],editKey=null,editDefault=null,returnCart=null;
 const money=n=>(n/100).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
 function snapshot(){return {options:[...current.querySelectorAll('[data-product-option]:checked')].map(o=>({id:o.value,name:o.dataset.optionName,price:Number(o.dataset.optionPrice||0)})),notes:current.querySelector('[data-product-notes]')?.value||'',utensils:!!current.querySelector('[data-utensils158]')?.checked};}
 function showDraft(value){current.querySelectorAll('[data-product-option]').forEach(o=>o.checked=!o.disabled&&!!value?.options?.some(v=>String(v.id)===o.value));const notes=current.querySelector('[data-product-notes]');if(notes)notes.value=value?.notes||'';const utensils=current.querySelector('[data-utensils158]');if(utensils)utensils.checked=!!value?.utensils;update();}
 function update(){if(!current)return;const config=snapshot(),extras=config.options.reduce((s,o)=>s+o.price,0),base=Number(current.dataset.price)||0;const summary=current.querySelector('[data-dish-summary151]');summary.querySelector('[data-base151]').textContent=money(base);summary.querySelector('[data-extras151]').textContent=money(extras);summary.querySelector('[data-total151]').textContent=money(base+extras);title.textContent=total>1?'Lanche '+(index+1)+' de '+total:'Personalizar';countInput.disabled=!!editKey||index>0;current.querySelector('[data-add]').textContent=index<total-1?'Próximo lanche →':(editKey?'Salvar alterações':'Adicionar '+(total>1?total+' lanches':'ao carrinho'))+' · '+money(drafts.reduce((sum,d,i)=>sum+(i!==index&&d?base+d.options.reduce((v,o)=>v+o.price,0):0),base+extras));current.querySelector('[data-prev160]').hidden=index===0;}
 function restore(){if(!current)return;marker.replaceWith(current);current.classList.remove('nu151-dish-open');current=null;marker=null;window.scrollTo({top:oldScroll,behavior:'instant'});if(returnCart){returnCart.showModal();returnCart=null;}}
 function close(){dialog.close();restore();}
 dialog.addEventListener('close',restore);header.querySelector('[data-close160]').addEventListener('click',close);
 function begin(card,key=null){if(current||card.querySelector('[data-add]')?.disabled)return;if(!window.NOWUP_CART160)return;
  editKey=key;editDefault=key?window.NOWUP_CART160.get(key):null;if(key&&!editDefault)return;
  total=editDefault?.quantity||Math.max(1,Math.min(Number(card.dataset.max)||99,parseInt(card.querySelector('[data-product-quantity]')?.value,10)||1));index=0;drafts=Array.from({length:total},()=>null);oldScroll=window.scrollY;marker=document.createComment('produto');card.before(marker);current=card;dialog.append(card);card.classList.add('nu151-dish-open');
  countInput.max=String(Number(card.dataset.max)||99);countInput.value=String(total);const note=card.querySelector('.nu85-note');if(note)note.open=true;showDraft(editDefault);
  const cart=root.querySelector('[data-cart-dialog143]');if(cart?.open){returnCart=cart;cart.close();}dialog.showModal();
 }
 countInput.addEventListener('change',()=>{if(!current)return;const n=Number(countInput.value),max=Number(current.dataset.max)||99;if(!Number.isInteger(n)||n<1||n>max){countInput.value=String(total);return;}total=n;drafts=Array.from({length:total},()=>null);index=0;update();});
 cards.forEach(card=>{
  const options=card.querySelector('.product-options');if(options){const t=options.querySelector('small');if(t)t.textContent='ADICIONAIS';const hint=document.createElement('small');hint.textContent='Opcional · Até 3 · Uma porção de cada';options.prepend(hint);}
  const note=card.querySelector('.nu85-note');if(note){const label=note.querySelector('label');if(label?.firstChild)label.firstChild.textContent='OBSERVAÇÕES / RETIRAR INGREDIENTES ';const input=note.querySelector('textarea');if(input)input.placeholder='Ex.: sem cebola, por favor.';}
  const utensils=document.createElement('label');utensils.className='nu158-utensils';utensils.innerHTML='<input type="checkbox" data-utensils158> 🍴 Enviar talheres (garfo e faca)';note?.before(utensils);
  const summary=document.createElement('div');summary.dataset.dishSummary151='';summary.className='nu151-summary';summary.innerHTML='<p><span>Lanche</span><b data-base151></b></p><p><span>Adicionais</span><b data-extras151></b></p><p><strong>Total desta unidade</strong><strong data-total151></strong></p>';card.querySelector('.product-buy')?.before(summary);
  const error=document.createElement('p');error.dataset.dishError151='';error.setAttribute('role','status');card.querySelector('.product-buy')?.before(error);
  const previous=document.createElement('button');previous.type='button';previous.dataset.prev160='';previous.className='nu160-prev';previous.textContent='← Lanche anterior';previous.addEventListener('click',()=>{drafts[index]=snapshot();index--;showDraft(drafts[index]||editDefault);});card.querySelector('.product-buy')?.before(previous);
  const plus=document.createElement('button');plus.type='button';plus.className='nu151-choose btn primary';plus.textContent='+';plus.setAttribute('aria-label','Personalizar '+card.dataset.name);plus.disabled=!!card.querySelector('[data-add]')?.disabled;plus.addEventListener('click',()=>begin(card));card.querySelector('.menu-product-info')?.append(plus);
  card.tabIndex=0;card.addEventListener('click',e=>{if(!dialog.open&&!e.target.closest('button,input,textarea,select,a,summary,label'))begin(card);});card.addEventListener('keydown',e=>{if(e.target===card&&(e.key==='Enter'||e.key===' ')){e.preventDefault();begin(card);}});
  card.querySelectorAll('[data-product-option]').forEach(o=>o.addEventListener('change',()=>{if(card.querySelectorAll('[data-product-option]:checked').length>3){o.checked=false;error.textContent='Escolha até 3 adicionais.';}else error.textContent='';update();}));
 });
 dialog.addEventListener('input',e=>{if(!e.target.matches('[data-amount160]'))update();});dialog.addEventListener('change',e=>{if(!e.target.matches('[data-amount160]'))update();});
 document.addEventListener('click',e=>{const edit=e.target.closest('[data-edit-personalization160]');if(!edit)return;const key=edit.dataset.editPersonalization160,value=window.NOWUP_CART160?.get(key),card=cards.find(c=>Number(c.dataset.id)===value?.productId);if(card){e.preventDefault();begin(card,key);}},true);
 root.addEventListener('click',e=>{const add=e.target.closest('[data-add]');if(!current||!add||!current.contains(add))return;e.preventDefault();e.stopImmediatePropagation();const config=snapshot();if(config.options.length>3)return;drafts[index]=config;
  if(index<total-1){index++;showDraft(drafts[index]||editDefault);return;}
  try{window.NOWUP_CART160.commit(current,drafts,editKey);close();}catch(err){current.querySelector('[data-dish-error151]').textContent=err.message;}
 },true);
})();
