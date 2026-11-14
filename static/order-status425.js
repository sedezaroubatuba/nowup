/* Update the open order without navigating away from its receipt. */
(()=>{'use strict';let busy=false;
 document.addEventListener('submit',async event=>{
 const form=event.target;if(!form.matches('[data-status-form425]'))return;
 event.preventDefault();event.stopImmediatePropagation();if(busy||!form.reportValidity())return;
 const section=form.closest('[data-order-status425]'),feedback=section.querySelector('[data-feedback425]'),body=new FormData(form);
 if(event.submitter?.name)body.set(event.submitter.name,event.submitter.value);
 busy=true;const buttons=[...section.querySelectorAll('button')];buttons.forEach(b=>b.disabled=true);feedback.textContent='Salvando…';
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),15000);
 try{
 const response=await fetch(form.action,{method:'POST',credentials:'same-origin',headers:{Accept:'application/json'},body,signal:controller.signal});
 const data=await response.json();if(!response.ok||data.status!==body.get('status'))throw Error(typeof data.detail==='string'?data.detail:'Confira o status atual antes de tentar novamente.');
 window.dispatchEvent(new CustomEvent('nowup:order-status',{detail:{id:Number(form.action.match(/pedidos\/(\d+)/)[1]),status:data.status}}));
 const page=await fetch(location.pathname,{credentials:'same-origin',cache:'no-store',signal:controller.signal});if(!page.ok)throw Error('Status salvo. Atualize este pedido para conferir.');
 const doc=new DOMParser().parseFromString(await page.text(),'text/html'),fresh=doc.querySelector('[data-order-status425]');if(!fresh)throw Error('Status salvo. Atualize este pedido para conferir.');
 const receipt=document.querySelector('.nu401-receipt'),nextReceipt=doc.querySelector('.nu401-receipt');
 if(receipt&&nextReceipt)receipt.replaceWith(nextReceipt);else section.replaceWith(fresh);
 for(const selector of ['.nu401-paper','#orderLiveStatus']){const old=document.querySelector(selector),next=doc.querySelector(selector);if(old&&next)old.replaceWith(next);}
 fresh.querySelector('[data-feedback425]').textContent='Status atualizado.';window.dispatchEvent(new Event('focus'));
 }catch(error){feedback.textContent=error.name==='AbortError'?'A resposta demorou. Confira o status antes de tentar novamente.':error.message;}
 finally{clearTimeout(timer);busy=false;buttons.forEach(b=>b.disabled=false);}
 },true);
})();
