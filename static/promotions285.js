/* Product promotion editor; the server calculates and validates the final price again. */
(()=>{'use strict';
 const cents=raw=>{let value=String(raw||'').replace(/R\$|\s/g,'');if(value.includes(','))value=value.replace(/\./g,'').replace(',','.');return Math.round(Number(value)*100);};
 const money=value=>(value/100).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
 document.querySelectorAll('[data-promotion285]').forEach(box=>{
  const form=box.closest('form'),base=form.querySelector('[name=price]'),enabled=box.querySelector('[data-promo-enabled285]'),settings=box.querySelector('[data-promo-settings285]'),final=box.querySelector('[name=promo_price]'),percent=box.querySelector('[name=promo_percent]'),error=box.querySelector('[data-promo-error285]');
  function refresh(){
   const active=enabled.checked,mode=box.querySelector('[name=promo_mode]:checked')?.value||'final',original=cents(base.value);settings.hidden=!active;
   box.querySelector('[data-promo-final285]').hidden=mode!=='final';box.querySelector('[data-promo-percent285]').hidden=mode!=='percent';
   final.disabled=!active||mode!=='final';percent.disabled=!active||mode!=='percent';final.required=active&&mode==='final';percent.required=active&&mode==='percent';
   const discount=Number(percent.value.replace(',','.')),value=mode==='percent'?Math.round(original*(100-discount)/100):cents(final.value),valid=Number.isFinite(original)&&original>0&&Number.isFinite(value)&&value>0&&value<original&&(mode!=='percent'||discount>0&&discount<100);
   box.querySelector('[data-promo-result285]').textContent=valid?money(value):'—';box.querySelector('[data-promo-original285]').textContent=valid?money(original):'';box.querySelector('[data-promo-saving285]').textContent=valid?'Economia de '+money(original-value)+' por unidade':'';
   const target=mode==='percent'?percent:final;final.setCustomValidity('');percent.setCustomValidity('');if(active&&!valid&&target.value)target.setCustomValidity('Confira o desconto: o preço final deve ser maior que zero e menor que o preço normal.');error.textContent=active&&!valid&&target.value?'Confira o desconto e o preço normal.':'';
  }
  box.addEventListener('input',refresh);box.addEventListener('change',refresh);base.addEventListener('input',refresh);refresh();
 });
})();
