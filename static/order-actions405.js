/* Persist actions first, then update only the order that was changed. */
(()=>{'use strict';
 document.addEventListener('click',async event=>{
  const link=event.target.closest('[data-board228] a[href*="abrir_pedido="]');if(!link)return;
  event.preventDefault();if(link.dataset.busy405)return;link.dataset.busy405='1';
  try{const r=await fetch(link.href,{credentials:'same-origin',cache:'no-store'});if(!r.ok)throw Error();const doc=new DOMParser().parseFromString(await r.text(),'text/html'),id=new URL(link.href).hash.slice(1),fresh=doc.getElementById(id);if(!fresh)throw Error();const old=document.getElementById(id),list=document.querySelector('.orders-list');if(old)old.replaceWith(fresh);else if(list)list.prepend(fresh);else throw Error();location.hash=id;window.dispatchEvent(new Event('hashchange'));fresh.scrollIntoView({block:'start'});}
  catch(_){const note=document.createElement('p');note.textContent='Não foi possível abrir o pedido. Tente novamente.';link.after(note);}finally{delete link.dataset.busy405;}
 });
 document.addEventListener('submit',async event=>{
  const form=event.target;if(event.defaultPrevented||!form.matches('form[method="post"]'))return;
  const path=new URL(form.action,location.href).pathname;
  if(!/^\/painel\/pedidos\/\d+\/(status|editar|conferir-pix|revisao)$/.test(path)||form.hasAttribute('data-change228'))return;
  event.preventDefault();if(form.dataset.busy405)return;
  if(form.hasAttribute('data-cancel-form')&&!form.querySelector('[name=reason]')?.value.trim()){
   form.dataset.busy405='1';const reason=await window.NowUpDialog.prompt('Informe o motivo da recusa:','',{required:true,title:'Recusar pedido',confirm:'Recusar pedido'});delete form.dataset.busy405;if(!reason?.trim())return;form.querySelector('[name=reason]').value=reason.trim();
  }
  const body=new FormData(form),submitter=event.submitter;
  if(submitter?.name)body.set(submitter.name,submitter.value);
  form.dataset.busy405='1';const buttons=[...form.querySelectorAll('button')];buttons.forEach(b=>b.disabled=true);
  let feedback=form.querySelector('[data-feedback405]');if(!feedback){feedback=document.createElement('p');feedback.dataset.feedback405='';feedback.setAttribute('role','status');form.append(feedback);}feedback.textContent='Salvando…';
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),15000);
  try{
   const r=await fetch(form.action,{method:'POST',body,credentials:'same-origin',signal:controller.signal});
   if(!r.ok){let message='Não foi possível salvar. Tente novamente.';try{message=(await r.json()).detail||message;}catch(_){}throw Error(message);}
   const url=new URL(r.url);if(url.pathname==='/entrar')throw Error('Entre novamente para continuar.');if(url.searchParams.has('erro'))throw Error('O pedido mudou. Confira os dados antes de continuar.');
   const doc=new DOMParser().parseFromString(await r.text(),'text/html');
   const card=form.closest('.order-card[id]'),track=document.querySelector('[data-order-link377]');
   if(card){const fresh=doc.getElementById(card.id);if(!fresh)throw Error('Status salvo. Atualize os pedidos para conferir.');card.replaceWith(fresh);}
   else if(track){window.dispatchEvent(new Event('focus'));feedback.textContent='Atualização salva.';}
   else {const old=document.querySelector('.nu401-paper'),fresh=doc.querySelector('.nu401-paper');if(old&&fresh)old.replaceWith(fresh);form.replaceChildren(Object.assign(document.createElement('p'),{textContent:'✓ Pix confirmado — recebimento registrado.'}));}
  }catch(error){feedback.textContent=error.name==='AbortError'?'Confira o status antes de tentar novamente: a resposta demorou.':error.message;}
  finally{clearTimeout(timer);delete form.dataset.busy405;buttons.forEach(b=>b.disabled=false);}
 });
})();
