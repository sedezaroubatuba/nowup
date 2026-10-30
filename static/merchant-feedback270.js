/* Keep delivery validation in the form, preserving the merchant's input. */
(()=>{'use strict';const root=document.getElementById('bairros-entrega265');if(!root)return;
 const forms=[...root.querySelectorAll('form')].filter(f=>f.getAttribute('action')==='/painel/cardapio/entregas89');
 const key=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('pt-BR').trim().replace(/\s+/g,' ');
 const existing=forms.filter(f=>f.elements.zone_id).map(f=>({id:String(f.elements.zone_id.value),name:f.elements.name.value}));
 function notice(form,text){let box=form.querySelector('[data-feedback270]');if(!box){box=document.createElement('p');box.dataset.feedback270='';box.className='nu270-feedback';box.setAttribute('role','alert');box.tabIndex=-1;form.prepend(box);}box.textContent=text;box.hidden=false;box.focus();box.scrollIntoView({block:'nearest',behavior:'smooth'});}
 for(const form of forms){let busy=false;form.addEventListener('submit',async event=>{event.preventDefault();if(busy)return;
  const id=String(form.elements.zone_id?.value||'');if(existing.some(z=>z.id!==id&&key(z.name)===key(form.elements.name.value))){notice(form,'Este bairro já foi cadastrado. Abra “Editar '+form.elements.name.value+'” na lista de bairros atendidos.');return;}
  busy=true;const buttons=[...form.querySelectorAll('button[type="submit"],button:not([type])')],previous=buttons.map(b=>b.disabled);buttons.forEach(b=>b.disabled=true);form.setAttribute('aria-busy','true');
  const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),20000);
  try{const response=await fetch(form.action,{method:'POST',body:new FormData(form),credentials:'same-origin',headers:{Accept:'application/json'},signal:controller.signal});
   if(response.redirected&&response.ok){const url=new URL(response.url,location.origin);if(url.origin===location.origin){location.assign(url.href);return;}}
   if(!response.ok){let text='Não foi possível salvar. Confira os dados e tente novamente.';try{const data=await response.json();if(typeof data.detail==='string'&&response.status<500)text=data.detail;else if(response.status===422)text='Confira o bairro, a taxa e o prazo informados.';}catch(_){}notice(form,text);return;}
   notice(form,'Confira a lista de bairros para confirmar se foi salvo antes de tentar novamente.');
  }catch(_){notice(form,'Não conseguimos confirmar o salvamento. Confira a lista de bairros antes de tentar novamente.');}
  finally{clearTimeout(timeout);busy=false;buttons.forEach((b,i)=>b.disabled=previous[i]);form.removeAttribute('aria-busy');}
 });}
})();
