/* NowUp v261: parent-first setup, optional product assignment and bulk actions. */
document.addEventListener('DOMContentLoaded',()=>{
  document.querySelectorAll('[data-subcats-admin261]').forEach(manager=>{
    const category=manager.querySelector('[data-subcats-category261]');
    const content=manager.querySelector('[data-subcats-content261]');
    const sectors=[...manager.querySelectorAll('[data-subcats-sector261]')];
    function showSector(){
      const chosen=category?.value||'';
      if(content)content.hidden=!chosen;
      sectors.forEach(section=>{
        section.hidden=section.dataset.subcatsSector261!==chosen;
        if(section.hidden){
          const form=section.querySelector('[data-subcats-add-form261]');
          const toggle=section.querySelector('[data-subcats-add-toggle261]');
          if(form)form.hidden=true;
          if(toggle)toggle.setAttribute('aria-expanded','false');
        }
      });
    }
    category?.addEventListener('change',showSector);
    showSector();
    manager.querySelectorAll('[data-subcats-add-toggle261]').forEach(btn=>{
      btn.addEventListener('click',()=>{
        const form=btn.closest('[data-subcats-sector261]')?.querySelector('[data-subcats-add-form261]');
        if(!form)return;
        form.hidden=!form.hidden;
        btn.setAttribute('aria-expanded',String(!form.hidden));
        if(!form.hidden)form.querySelector('input[name="name"]')?.focus();
      });
    });
  });

  document.querySelectorAll('[data-subcat-picker261]').forEach(picker=>{
    const form=picker.closest('form');
    const parent=form?.querySelector('select[name="category"]');
    const options=[...picker.options].map(o=>({value:o.value,label:o.textContent,category:o.dataset.parent261||''}));
    function populate(wanted){
      const chosen=(parent?.value||'').trim().toLocaleLowerCase('pt-BR');
      picker.replaceChildren();
      options.filter(o=>!o.value||o.category.trim().toLocaleLowerCase('pt-BR')===chosen).forEach(o=>{
        picker.add(new Option(o.label,o.value));
      });
      picker.value=[...picker.options].some(o=>o.value===wanted)?wanted:'0';
      // If this category has no subcategories, keep the optional field out of the way.
      const field=picker.closest('[data-subcat-field261]');
      if(field)field.hidden=picker.options.length<=1;
    }
    populate(picker.dataset.selected261||picker.value||'0');
    parent?.addEventListener('change',()=>populate('0'));
  });

  document.querySelectorAll('[data-bulk261]').forEach(form=>{
    form.querySelector('[data-all261]')?.addEventListener('click',()=>{
      form.querySelectorAll('input[name="product_ids"]').forEach(o=>o.checked=true);
    });
    form.querySelector('[data-none261]')?.addEventListener('click',()=>{
      form.querySelectorAll('input[name="product_ids"]').forEach(o=>o.checked=false);
    });
  });
});
/* V449: return directly to the category a merchant just edited. */
document.addEventListener('DOMContentLoaded',()=>{
  const selected=new URLSearchParams(location.search).get('categoria449');
  if(!selected||!/^[0-9]+$/.test(selected))return;
  const card=document.querySelector('[data-category449="'+selected+'"]');
  if(!card)return;
  const manager=document.getElementById('categorias-loja');
  if(manager)manager.open=true;
  card.open=true;
  requestAnimationFrame(()=>card.scrollIntoView({block:'nearest',behavior:'instant'}));
});
