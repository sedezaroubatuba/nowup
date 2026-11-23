/* NowUp 260: group promotion selection, with no new checkout/cart logic. */
document.addEventListener('click',event=>{
  const trigger=event.target.closest('[data-select-all260],[data-unselect-all260]');
  if(!trigger)return;
  const form=trigger.closest('form');
  if(!form)return;
  const checked=trigger.hasAttribute('data-select-all260');
  form.querySelectorAll('input[name="item_ids"]').forEach(el=>{el.checked=checked;});
});

/* Return to the right group after saving, with the quick-add form above the collapsed list. */
document.addEventListener('DOMContentLoaded',()=>{
  const params=new URLSearchParams(window.location.search);
  const id=params.get('grupo260');
  if(!id||!/^[0-9]+$/.test(id))return;
  const editor=document.getElementById('grupo260-'+id);
  if(!editor)return;
  editor.open=true;
  if(params.get('novo260')==='1')editor.querySelector('.nu-group260-add')?.setAttribute('open','');
  if(params.get('itens260')==='1')editor.querySelector('.nu-group260-members')?.setAttribute('open','');
  requestAnimationFrame(()=>editor.scrollIntoView({block:'start',behavior:'auto'}));
});
