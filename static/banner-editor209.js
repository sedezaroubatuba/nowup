document.querySelectorAll('.b207 form').forEach(form=>{
 const select=form.querySelector('[name=mode]'),fieldset=form.querySelector('fieldset');
 function sync(){if(fieldset){fieldset.hidden=select.value==='info';fieldset.disabled=select.value==='info';}}
 if(select){select.addEventListener('change',sync);sync();}
 form.addEventListener('submit',async event=>{
  event.preventDefault();let message=form.querySelector('[data-feedback209]');if(!message){message=document.createElement('p');message.dataset.feedback209='1';message.setAttribute('role','alert');form.append(message);}
  const buttons=[...form.querySelectorAll('button')],payload=new FormData(form);buttons.forEach(b=>b.disabled=true);message.textContent='Salvando…';
  try{const r=await fetch(form.action,{method:'POST',body:payload,credentials:'same-origin'});
   if(r.redirected&&r.ok){location.assign(r.url);return;}
   if(!r.ok){let text='Não foi possível salvar. Confira os campos e tente novamente.';try{const d=await r.json();if(typeof d.detail==='string')text=d.detail;}catch(_){}message.textContent=text;}
   else{location.assign('/painel/banners?salvo=1');return;}
  }catch(_){message.textContent='Falha de conexão. Seus campos continuam preenchidos; tente novamente.';}
  finally{buttons.forEach(b=>b.disabled=false);}
 });
});
