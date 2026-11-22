/* NowUp 260: group promotion selection, with no new checkout/cart logic. */
document.addEventListener('click',event=>{
  const trigger=event.target.closest('[data-select-all260],[data-unselect-all260]');
  if(!trigger)return;
  const form=trigger.closest('form');
  if(!form)return;
  const checked=trigger.hasAttribute('data-select-all260');
  form.querySelectorAll('input[name="item_ids"]').forEach(el=>{el.checked=checked;});
});
