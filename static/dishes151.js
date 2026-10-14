(() => {
 'use strict';
 const root=document.querySelector('[data-native-menu]');if(!root)return;
 const dishes=[...root.querySelectorAll('[data-product][data-dish="1"]')];if(!dishes.length)return;
 const dialog=document.createElement('dialog');dialog.className='nu151-dish-dialog';dialog.setAttribute('aria-label','Personalizar prato');
 const close=document.createElement('button');close.type='button';close.className='nu151-close';close.textContent='×';close.setAttribute('aria-label','Voltar ao cardápio');dialog.append(close);root.append(dialog);
 let current=null,marker=null,scroll=0;
 const money=c=>(c/100).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
 function restore(){if(!current)return;marker.replaceWith(current);current.classList.remove('nu151-dish-open');current=null;marker=null;window.scrollTo({top:scroll,behavior:'instant'});}
 function dismiss(){dialog.close();restore();}
 dialog.addEventListener('close',restore);close.addEventListener('click',dismiss);
 function update(){if(!current)return;const base=Number(current.dataset.price)||0,extras=[...current.querySelectorAll('[data-product-option]:checked')].reduce((sum,o)=>sum+Number(o.dataset.optionPrice||0),0),quantity=Math.max(1,Math.min(Number(current.dataset.max)||99,parseInt(current.querySelector('[data-product-quantity]')?.value,10)||1));
 const summary=current.querySelector('[data-dish-summary151]');summary.querySelector('[data-base151]').textContent=money(base);summary.querySelector('[data-extras151]').textContent=money(extras);summary.querySelector('[data-total151]').textContent=money((base+extras)*quantity);current.querySelector('[data-add]').textContent='Adicionar ao carrinho · '+money((base+extras)*quantity);}
 function open(card){if(current)return;scroll=window.scrollY;marker=document.createComment('prato');card.before(marker);current=card;dialog.append(card);card.classList.add('nu151-dish-open');update();dialog.showModal();}
 dishes.forEach(card=>{
  const options=card.querySelector('.product-options');if(options){const title=options.querySelector('small');if(title)title.textContent='Personalize seu prato';card.querySelectorAll('[data-dish-group]').forEach(g=>{const hint=document.createElement('small');hint.textContent=g.dataset.groupName+' · '+(Number(g.dataset.min)===0?'Opcional':'Obrigatório')+' · Escolha até '+g.dataset.max+' opções';options.insertBefore(hint,options.querySelector('label'));});}
  const summary=document.createElement('div');summary.dataset.dishSummary151='';summary.className='nu151-summary';summary.innerHTML='<p><span>Prato por unidade</span><b data-base151></b></p><p><span>Adicionais por unidade</span><b data-extras151></b></p><p><strong>Total</strong><strong data-total151></strong></p>';card.querySelector('.product-buy')?.before(summary);
  const choose=document.createElement('button');choose.type='button';choose.className='btn primary nu151-choose';choose.textContent='Escolher prato e adicionais';choose.disabled=!!card.querySelector('[data-add]')?.disabled;choose.addEventListener('click',()=>open(card));card.querySelector('.menu-product-info')?.append(choose);
  card.querySelectorAll('[data-product-option]').forEach(o=>o.addEventListener('change',()=>{const group=[...card.querySelectorAll('[data-dish-group]')].find(g=>g.dataset.dishGroup===o.dataset.optionGroup);if(group&&o.checked){const count=[...card.querySelectorAll('[data-product-option]:checked')].filter(x=>x.dataset.optionGroup===o.dataset.optionGroup).length;if(count>Number(group.dataset.max)){o.checked=false;card.querySelector('[data-dish-error151]').textContent='Escolha até '+group.dataset.max+' opções em '+group.dataset.groupName+'.';}}update();}));
  const error=document.createElement('p');error.dataset.dishError151='';error.setAttribute('role','status');card.querySelector('.product-buy')?.before(error);
 });
 dialog.addEventListener('input',update);dialog.addEventListener('change',update);
 root.addEventListener('click',event=>{const button=event.target.closest('[data-add]');if(!button||!current||!current.contains(button))return;
  for(const group of current.querySelectorAll('[data-dish-group]')){const count=[...current.querySelectorAll('[data-product-option]:checked')].filter(o=>o.dataset.optionGroup===group.dataset.dishGroup).length;if(count<Number(group.dataset.min)||count>Number(group.dataset.max)){event.preventDefault();event.stopImmediatePropagation();current.querySelector('[data-dish-error151]').textContent=group.dataset.groupName+': escolha de '+group.dataset.min+' a '+group.dataset.max+' opções.';return;}}
  setTimeout(dismiss,0);
 },true);
})();
