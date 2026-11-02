/* V328: keep catalog registrations in their own editor after saving. */
(()=>{'use strict';
 const key='nowup:catalog-return328';
 document.addEventListener('submit',event=>{
  const form=event.target;
  if(event.defaultPrevented||!form.closest('.pro-dashboard'))return;
  const url=new URL(form.action,location.href);
  if(!/^\/painel\/cardapio\/(produtos(?:\/\d+)?|ingredientes320)$/.test(url.pathname))return;
  if(form.dataset.saving328){event.preventDefault();return;}
  const editor=form.closest('[data-product-id]');
  let target=editor?.id|| (form.dataset.mealEditor322==='1'?'novo-lanche322':url.pathname.endsWith('ingredientes320')?'ingredientes320':form.dataset.comboEditor301?'cadastrar-combo':'novo-produto');
  url.searchParams.set('return_to328',target);form.action=url.pathname+url.search;
  try{sessionStorage.setItem(key,JSON.stringify({target,time:Date.now(),scroll:window.scrollY}));}catch(_){}
  form.dataset.saving328='1';form.setAttribute('aria-busy','true');
  const button=event.submitter;if(button){button.dataset.label328=button.textContent;button.disabled=true;button.textContent='Salvando…';}
 });
 window.addEventListener('pageshow',()=>document.querySelectorAll('[data-saving328]').forEach(form=>{
  delete form.dataset.saving328;form.removeAttribute('aria-busy');form.querySelectorAll('[data-label328]').forEach(button=>{button.textContent=button.dataset.label328;button.disabled=false;delete button.dataset.label328;});
 }));
 const ok=new URLSearchParams(location.search).get('ok');
 if(['produto','refeicao','combo','ingrediente'].includes(ok)){
  let state;try{state=JSON.parse(sessionStorage.getItem(key)||'null');sessionStorage.removeItem(key);}catch(_){}
  const target=document.getElementById(location.hash.slice(1));
  if(target){
   for(let node=target;node;node=node.parentElement)if(node.tagName==='DETAILS')node.open=true;
   window.NOWUP_EDITORS328?.(target);window.NOWUP_COMPACT328?.(target);
   const message=document.createElement('p');message.setAttribute('role','status');message.textContent='Salvo com sucesso! Você pode continuar cadastrando ou editando aqui.';const summary=target.querySelector(':scope > summary');if(summary)summary.after(message);else target.prepend(message);
   requestAnimationFrame(()=>{window.dispatchEvent(new Event('nowup:panelnavigate'));requestAnimationFrame(()=>{
    if(state?.target===target.id&&Date.now()-state.time<120000)window.scrollTo({top:state.scroll,behavior:'auto'});
    else target.scrollIntoView({block:'start',behavior:'auto'});
   });});
  }
 }
 if(ok==='categoria-ordenada'){const box=document.getElementById('categorias-loja');if(box)box.open=true;}
})();
