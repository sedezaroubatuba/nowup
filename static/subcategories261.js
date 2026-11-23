/* NowUp v261: parent-first setup, optional product assignment and bulk actions. */
document.addEventListener('DOMContentLoaded',()=>{
  // V449: the category itself owns the add-subcategory control.
  document.querySelectorAll('#categorias-loja .nu449-category-details').forEach(detail=>{
    const button=detail.querySelector('[data-subcats-add-toggle261]');
    const form=detail.querySelector('[data-subcats-add-form261]');
    if(!button||!form)return;
    button.addEventListener('click',()=>{
      form.hidden=!form.hidden;
      button.setAttribute('aria-expanded',String(!form.hidden));
      if(!form.hidden)form.querySelector('input[name="name"]')?.focus();
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