/* NowUp 260: group promotion selection, with no new checkout/cart logic. */
document.addEventListener('click',event=>{
  const trigger=event.target.closest('[data-select-all260],[data-unselect-all260]');
  if(!trigger)return;
  const form=trigger.closest('form');
  if(!form)return;
  const checked=trigger.hasAttribute('data-select-all260');
  form.querySelectorAll('input[name="item_ids"]').forEach(el=>{el.checked=checked;});
});

/* V451: many individually priced products under the same cover photo. */
document.addEventListener('click',event=>{
  const add=event.target.closest('[data-add-variant451]');
  const remove=event.target.closest('[data-remove-variant451]');
  if(!add&&!remove)return;
  const builder=event.target.closest('[data-variant-builder451]');
  const list=builder?.querySelector('[data-variant-list451]');
  if(!list)return;
  if(add){
    if(list.children.length>=80){alert('Máximo de 80 variações por agrupador.');return;}
    const row=list.firstElementChild.cloneNode(true);
    row.querySelectorAll('input').forEach(i=>i.value='');
    list.append(row);
    row.querySelector('input[name="variant_names"]')?.focus();
  }else if(remove){
    if(list.children.length<=1)return;
    remove.closest('.nu260-variant-row')?.remove();
  }
});
