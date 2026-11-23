/* V454: preserve the merchant's category and continue with the next visible product after saving. */
(()=>{'use strict';
 const key='nowup:catalog-return328';
 const normalize=value=>String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').trim().toLowerCase();
 const visible=card=>!!card&&card.isConnected&&!card.hidden&&card.style.display!=='none';
 const listCards=editor=>{
  if(!editor)return [];
  return [...editor.parentElement.querySelectorAll(':scope > [data-product-id]')].filter(visible);
 };
 document.addEventListener('submit',event=>{
  const form=event.target;
  if(event.defaultPrevented||!form.closest('.pro-dashboard'))return;
  const url=new URL(form.action,location.href);
  if(!/^\/painel\/cardapio\/(produtos(?:\/\d+(?:\/disponibilidade)?)?|ingredientes320)$/.test(url.pathname))return;
  if(form.dataset.saving328){event.preventDefault();return;}
  const editor=form.closest('[data-product-id]'),list=!!editor?.closest('[data-pro-products]');
  const target=editor?.id||(form.dataset.mealEditor322==='1'?'novo-lanche322':url.pathname.endsWith('ingredientes320')?'ingredientes320':form.dataset.comboEditor301?'cadastrar-combo':'novo-produto');
  const cards=listCards(editor),index=cards.indexOf(editor);
  const next=index>=0?cards[index+1]:null,previous=index>0?cards[index-1]:null;
  const filters=[...document.querySelectorAll('[data-pro-category].active')].map(n=>n.dataset.proCategory);
  const searches=[...document.querySelectorAll('[data-pro-search],[data-search-combos301]')].map(n=>n.value);
  const category=window.NOWUP_PRO_PRODUCT_FILTERS?.current?.()||filters[0]||'all';
  const previousCategory=editor?.dataset.category||'',newCategory=form.querySelector('select[name="category"]')?.value||previousCategory;
  // Editors in the ordinary-product list always return to that list, not to a
  // moved product that has ceased to belong to the previous category.
  url.searchParams.set('return_to328',list?'produtos-loja':target);
  form.action=url.pathname+url.search;
  try{sessionStorage.setItem(key,JSON.stringify({
   target,time:Date.now(),scroll:window.scrollY,
   next:next?.id,previous:previous?.id,filters,searches,list,category,
   previousCategory,newCategory
  }));}catch(_){}
  form.dataset.saving328='1';form.setAttribute('aria-busy','true');
  const button=event.submitter;
  if(button){button.dataset.label328=button.textContent;button.disabled=true;button.textContent='Salvando…';}
 });
 window.addEventListener('pageshow',()=>document.querySelectorAll('[data-saving328]').forEach(form=>{
  delete form.dataset.saving328;form.removeAttribute('aria-busy');
  form.querySelectorAll('[data-label328]').forEach(button=>{
   button.textContent=button.dataset.label328;button.disabled=false;delete button.dataset.label328;
  });
 }));
 const ok=new URLSearchParams(location.search).get('ok');
 if(!['produto','refeicao','combo','ingrediente','disponibilidade'].includes(ok)){
  if(ok==='categoria-ordenada'){const box=document.getElementById('categorias-loja');if(box)box.open=true;}
  return;
 }
 let state;
 try{state=JSON.parse(sessionStorage.getItem(key)||'null');sessionStorage.removeItem(key);}catch(_){}
 const fresh=state&&Date.now()-state.time<120000&&state.time<=Date.now();
 function openEditor(target,message){
  if(!target)return;
  for(let node=target;node;node=node.parentElement)if(node.tagName==='DETAILS')node.open=true;
  window.NOWUP_EDITORS328?.(target);window.NOWUP_COMPACT328?.(target);
  if(!message)return;
  const status=document.createElement('p');status.setAttribute('role','status');status.textContent=message;
  const summary=target.querySelector(':scope > summary');
  if(summary)summary.after(status);else target.prepend(status);
 }
 function restoreOtherEditors(){
  if(fresh){
   for(const value of state.filters||[])document.querySelectorAll('[data-pro-category]').forEach(button=>{
    if(button.dataset.proCategory===value)button.click();
   });
   document.querySelectorAll('[data-pro-search],[data-search-combos301]').forEach((input,i)=>{
    input.value=state.searches?.[i]||'';
    input.dispatchEvent(new Event('input',{bubbles:true}));
   });
  }
  const target=document.getElementById(fresh?(state.next||state.target):location.hash.slice(1));
  if(target){
   openEditor(target,'Salvo com sucesso! Continue a edição neste produto.');
   if(fresh)history.replaceState(null,'','#'+target.id);
   window.dispatchEvent(new Event('nowup:panelnavigate'));
   requestAnimationFrame(()=>requestAnimationFrame(()=>{
    if(!state?.next&&state?.target===target.id&&fresh)window.scrollTo({top:state.scroll,behavior:'auto'});
    else target.scrollIntoView({block:'start',behavior:'auto'});
   }));
  }
 }
 function restoreOrdinaryProducts(){
  const filters=window.NOWUP_PRO_PRODUCT_FILTERS;
  if(filters?.restore)filters.restore(state.category,state.searches?.[0]||'');
  else {
   const button=[...document.querySelectorAll('[data-pro-category]')].find(b=>b.dataset.proCategory===state.category);
   button?.click();
   const search=document.querySelector('[data-pro-search]');
   if(search){search.value=state.searches?.[0]||'';search.dispatchEvent(new Event('input',{bubbles:true}));}
  }
  // Do not reveal a product filtered out by its new category or by a saved search.
  const inList=id=>{
   const el=id&&document.getElementById(id);
   return el?.closest('[data-pro-products]')&&visible(el)?el:null;
  };
  const target=inList(state.next)||inList(state.previous)||inList(state.target)
   ||filters?.visibleCards?.().find(card=>card.id!==state.target)||null;
  // The merchant's category remains selected, even when it now has zero items.
  history.replaceState(null,'','#produtos-loja');
  window.dispatchEvent(new Event('nowup:panelnavigate'));
  const moved=state.previousCategory&&normalize(state.previousCategory)!==normalize(state.newCategory);
  const label=moved?'Produto salvo e movido para '+state.newCategory+'. ':'Alterações salvas. ';
  const message=label+(target?'Próximo produto pronto para edição.':'Você continua nesta categoria.');
  const header=document.getElementById('produtos-loja');
  if(header){
   const notice=document.createElement('p');notice.setAttribute('role','status');
   notice.className='nu454-product-saved';notice.textContent=message;header.append(notice);
  }
  if(target)openEditor(target,null);
  requestAnimationFrame(()=>requestAnimationFrame(()=>{
   const focus=target||header;
   if(focus?.isConnected)focus.scrollIntoView({block:'start',behavior:'auto'});
   if(target)target.querySelector(':scope > summary')?.focus({preventScroll:true});
  }));
 }
 function restore(){
  if(fresh&&state.list){restoreOrdinaryProducts();return;}
  restoreOtherEditors();
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',restore,{once:true});
 else requestAnimationFrame(restore);
})();
