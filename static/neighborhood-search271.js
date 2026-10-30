/* Filter only this store's delivery zones; typing never changes the chosen fee. */
(()=>{'use strict';const normalize=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('pt-BR').trim().replace(/\s+/g,' ');
 document.querySelectorAll('[data-delivery-zone265]').forEach((select,index)=>{
  if(select.dataset.search271)return;select.dataset.search271='1';
  const original=[...select.options].map(o=>o.cloneNode(true)),label=document.createElement('label'),input=document.createElement('input'),status=document.createElement('small');
  label.textContent='Buscar bairro';input.type='search';input.className='input';input.placeholder='Digite o nome do bairro';input.autocomplete='off';input.setAttribute('aria-controls',select.id||(select.id='delivery-zone271-'+index));
  status.id='zone-search-status271-'+index;status.setAttribute('role','status');status.setAttribute('aria-live','polite');input.setAttribute('aria-describedby',status.id);label.append(input,status);
  const field=select.closest('label')||select;field.parentNode.insertBefore(label,field);
  input.addEventListener('input',()=>{
   const chosen=select.value,query=normalize(input.value),matches=original.filter(o=>o.value&&normalize(o.textContent.split(' — ')[0]).includes(query));
   // Retain the current selection even when it is outside the filter, so the freight stays unchanged.
   const options=original.filter(o=>!o.value||o.value===chosen||matches.includes(o)).map(o=>o.cloneNode(true));
   select.replaceChildren(...options);select.value=chosen;
   status.textContent=query?(matches.length?matches.length+(matches.length===1?' bairro encontrado.':' bairros encontrados.'):'Nenhum bairro encontrado nesta loja.') :'';
   if(query&&chosen&&!matches.some(o=>o.value===chosen))status.textContent+=' Bairro selecionado mantido: '+chosen+'.';
  });
 });
})();
