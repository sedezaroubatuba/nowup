(()=>{
  const buttons=[...document.querySelectorAll('[data-pro-category]')],products=[...document.querySelectorAll('[data-pro-product]')];if(!buttons.length)return;
  const normalize=v=>String(v||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').trim().toLocaleLowerCase('pt-BR').replace(/\s+/g,' ');
  buttons.forEach(button=>button.addEventListener('click',()=>{const selected=normalize(button.dataset.proCategory);buttons.forEach(item=>item.classList.toggle('active',item===button));products.forEach(product=>{const category=normalize(product.dataset.category),promotion=product.dataset.featured==='1';product.hidden=selected!=='all'&&(selected==='promocoes'?!promotion:category!==selected)})}));
})();
