/* NowUp v261: subcategory selection in all merchant product forms. */
document.addEventListener('DOMContentLoaded',()=>{
  document.querySelectorAll('[data-subcat-picker261]').forEach(picker=>{
    const form=picker.closest('form');
    const parent=form?.querySelector('select[name="category"]');
    const all=Array.from(picker.options).map(o=>({value:o.value,label:o.textContent,category:o.dataset.parent261||''}));
    function populate(wanted){
      const parentName=(parent?.value||'').toLocaleLowerCase('pt-BR');
      picker.replaceChildren();
      all.filter(o=>!o.value||o.category.toLocaleLowerCase('pt-BR')===parentName).forEach(o=>{
        const option=new Option(o.label,o.value);picker.add(option);
      });
      picker.value=Array.from(picker.options).some(o=>o.value===wanted)?wanted:'0';
    }
    populate(picker.dataset.selected261||picker.value||'0');
    parent?.addEventListener('change',()=>populate('0'));
  });
  document.querySelectorAll('[data-bulk261]').forEach(form=>{
    form.querySelector('[data-all261]')?.addEventListener('click',()=>form.querySelectorAll('input[name="product_ids"]').forEach(o=>o.checked=true));
    form.querySelector('[data-none261]')?.addEventListener('click',()=>form.querySelectorAll('input[name="product_ids"]').forEach(o=>o.checked=false));
  });
});