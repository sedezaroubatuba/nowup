/* Bulk selection for each product's own paid-extra picker. */
(()=>{'use strict';
 const norm=s=>String(s).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim();
 const button=text=>{const b=document.createElement('button');b.type='button';b.className='btn soft';b.textContent=text;return b;};
 for(const box of document.querySelectorAll('[data-shared-picker155]')){
  const form=box.closest('form'),mode=form?.querySelector('[name=extras_mode]');if(!form||!mode)continue;
  let search=box.querySelector('input[type=search]');if(!search){search=document.createElement('input');search.type='search';search.className='input';search.placeholder='Buscar adicional cadastrado';search.setAttribute('aria-label','Buscar adicional cadastrado');box.prepend(search);}
  const tools=document.createElement('div');tools.className='nu443-tools';const all=button('Selecionar todos os resultados'),clear=button('Desmarcar resultados'),status=document.createElement('small');status.setAttribute('role','status');tools.append(all,clear,status);search.after(tools);
  const matches=()=>[...box.querySelectorAll('input[name=extra_ids]')].filter(c=>!c.disabled&&norm(c.closest('label')?.textContent||'').includes(norm(search.value)));
  const sync=()=>{const found=matches();all.textContent='Selecionar todos os resultados ('+found.length+')';all.disabled=clear.disabled=!found.length;status.textContent=box.querySelectorAll('input[name=extra_ids]:checked').length+' adicional(is) selecionado(s)';box.querySelectorAll('label').forEach(l=>{if(l.querySelector('[name=extra_ids]'))l.hidden=!norm(l.textContent).includes(norm(search.value));});};
  const set=value=>{matches().forEach(c=>{c.checked=value;});if(value)mode.value='selected';mode.dispatchEvent(new Event('change',{bubbles:true}));box.dispatchEvent(new Event('change',{bubbles:true}));sync();};
  all.onclick=()=>set(true);clear.onclick=()=>set(false);search.addEventListener('input',sync);box.addEventListener('change',sync);new MutationObserver(sync).observe(box,{childList:true});sync();
 }
 const style=document.createElement('style');style.textContent='.nu443-tools{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:10px 0}.nu443-tools button{white-space:normal!important;min-height:44px}.nu443-result{display:flex;align-items:center;gap:8px}.nu443-result>input[type=checkbox]{width:22px!important;height:22px!important;flex:0 0 22px}.nu443-result>.nu300-product-result{flex:1;min-width:0}';document.head.append(style);
})();
