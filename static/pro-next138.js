/* Saving returns to the catalog without reopening or refocusing registration. */
(()=>{'use strict';
 document.addEventListener('submit',event=>{
  const form=event.target;if(!form.matches('.pro-dashboard form[action^="/painel/cardapio/produtos"]')||event.defaultPrevented)return;
  if(form.dataset.saving326){event.preventDefault();return;}
  form.dataset.saving326='1';form.setAttribute('aria-busy','true');
  const button=event.submitter;if(button){button.dataset.label326=button.textContent;button.disabled=true;button.textContent='Salvando…';}
 });
 window.addEventListener('pageshow',()=>document.querySelectorAll('[data-saving326]').forEach(form=>{
  delete form.dataset.saving326;form.removeAttribute('aria-busy');form.querySelectorAll('[data-label326]').forEach(button=>{button.textContent=button.dataset.label326;button.disabled=false;delete button.dataset.label326;});
 }));
 const ok=new URLSearchParams(location.search).get('ok');
 if(ok==='produto'){
  const form=document.getElementById('novo-produto');if(form)form.open=false;
  const catalog=document.getElementById('produtos-loja');
  if(catalog){const message=document.createElement('p');message.setAttribute('role','status');message.textContent='Produto salvo com sucesso!';catalog.prepend(message);}
 }
 if(ok==='categoria-ordenada'){const box=document.getElementById('categorias-loja');if(box)box.open=true;}
})();
