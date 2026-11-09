document.querySelectorAll('.b207 form').forEach(form=>{
 const select=form.querySelector('[name=mode]'),fieldset=form.querySelector('fieldset'),products=form.querySelector('[data-products384]'),link=form.querySelector('[data-link384]');
 function sync(){const usesProducts=['single','selection'].includes(select.value);if(fieldset){fieldset.disabled=!usesProducts;}if(products)products.hidden=!usesProducts;if(link){link.hidden=select.value!=='link';const input=link.querySelector('input');input.disabled=select.value!=='link';input.required=select.value==='link';}}
 if(select){select.addEventListener('change',sync);sync();}
 const search=form.querySelector('[data-search384]'),searchStatus=form.querySelector('[data-search-status384]');
 const rows=[...form.querySelectorAll('[data-product384]')],normalize=value=>value.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('pt-BR');
 function filter(){const query=normalize(search.value.trim());let count=0;for(const row of rows){row.hidden=!normalize(row.textContent).includes(query);if(!row.hidden)count++;}const selected=rows.filter(row=>row.querySelector('input').checked).length;searchStatus.textContent=(count?count+' produto(s) encontrado(s).':'Nenhum produto encontrado.')+' '+selected+' selecionado(s).';}
 if(search){search.addEventListener('input',filter);fieldset.addEventListener('change',filter);filter();}
 const order=form.querySelector('[data-order-list384]');
 function refreshOrder(){if(!order)return;const items=[...order.children];items.forEach((item,i)=>{item.querySelector('[data-move384=up]').disabled=i===0;item.querySelector('[data-move384=down]').disabled=i===items.length-1;});}
 if(order){refreshOrder();order.addEventListener('click',event=>{const button=event.target.closest('[data-move384]');if(!button||button.disabled)return;const item=button.closest('[data-order-item384]');if(button.dataset.move384==='up'&&item.previousElementSibling)order.insertBefore(item,item.previousElementSibling);else if(button.dataset.move384==='down'&&item.nextElementSibling)order.insertBefore(item.nextElementSibling,item);refreshOrder();form.querySelector('[data-order-status384]').textContent='Ordem alterada. Toque em Salvar ordem para confirmar.';if(!button.disabled)button.focus();});}
 form.addEventListener('submit',async event=>{
  event.preventDefault();let message=form.querySelector('[data-feedback209]');if(!message){message=document.createElement('p');message.dataset.feedback209='1';message.setAttribute('role','alert');form.append(message);}
  const buttons=[...form.querySelectorAll('button')],payload=new FormData(form);buttons.forEach(b=>b.disabled=true);message.textContent='Salvando…';
  try{const r=await fetch(form.action,{method:'POST',body:payload,credentials:'same-origin'});
   if(r.redirected&&r.ok){location.assign(r.url);return;}
   if(!r.ok){let text='Não foi possível salvar. Confira os campos e tente novamente.';try{const d=await r.json();if(typeof d.detail==='string')text=d.detail;}catch(_){}message.textContent=text;}
   else{location.assign('/painel/banners?salvo=1');return;}
  }catch(_){message.textContent='Falha de conexão. Seus campos continuam preenchidos; tente novamente.';}
  finally{buttons.forEach(b=>b.disabled=false);refreshOrder();}
 });
});
