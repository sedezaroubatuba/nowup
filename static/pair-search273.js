/* Independent search in every product form; filtered selections remain submitted. */
(()=>{
 'use strict';
 const normalize=value=>String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim();
 function refresh(picker){
  const query=normalize(picker.querySelector('[data-pair-search273]').value);
  const rows=[...picker.querySelectorAll('[data-pair-option273]')];let visible=0,selected=0;
  rows.forEach(row=>{const match=normalize(row.querySelector('span').textContent).includes(query);row.hidden=!match;if(match)visible++;if(row.querySelector('input').checked)selected++;});
  picker.querySelector('[data-pair-status273]').textContent=(visible?visible+' produto(s) encontrado(s)':'Nenhum produto encontrado')+' · '+selected+' selecionado(s)';
 }
 document.addEventListener('input',e=>{if(e.target.matches('[data-pair-search273]'))refresh(e.target.closest('[data-pair-picker273]'));});
 document.addEventListener('change',e=>{const picker=e.target.closest('[data-pair-picker273]');if(picker)refresh(picker);});
 const start=()=>document.querySelectorAll('[data-pair-picker273]').forEach(refresh);
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();
