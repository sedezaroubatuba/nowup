/* Manual links only: never contact a WhatsApp/Meta API or claim delivery. */
(function(scope){'use strict';
 function phone(value){let n=String(value||'').replace(/\D/g,'');if(n.startsWith('00'))n=n.slice(2);if(n.length===10||n.length===11)n='55'+n;return /^55\d{10,11}$/.test(n)?n:'';}
 function message(template,values){return String(template||'').replace(/\{\{(nome_cliente|numero_pedido|nome_loja)\}\}/g,(_,key)=>String(values[key]??''));}
 function link(number,text){const n=phone(number);return n?'https://wa.me/'+n+'?text='+encodeURIComponent(text):'';}
 const api={phone,message,link};if(typeof module!=='undefined')module.exports=api;
 if(typeof document==='undefined')return;
 const defaults=document.getElementById('wa-defaults421');
 if(defaults){const data=JSON.parse(defaults.textContent);document.addEventListener('click',e=>{const button=e.target.closest('[data-restore421]');if(!button)return;const input=document.querySelector('[data-message421="'+button.dataset.restore421+'"]');if(input)input.value=data[button.dataset.restore421];});}
 const configNode=document.getElementById('wa-config421'),root=document.querySelector('[data-whatsapp-central418]');if(!configNode||!root)return;
 const config=JSON.parse(configNode.textContent),sent=new Map();
 function enhance(){root.querySelectorAll('[data-wa-status421]').forEach(box=>{const status=box.dataset.status421,number=phone(box.dataset.phone421),button=box.querySelector('[data-wa-send421]'),missing=box.querySelector('[data-wa-missing421]'),receipt=box.querySelector('[data-wa-sent421]');
  const template=config.templates[status];button.hidden=!config.enabled||!template||!number;missing.hidden=Boolean(number);if(!button.hidden){button.href=link(number,message(template,{nome_cliente:box.dataset.customer421,numero_pedido:box.dataset.code421,nome_loja:config.storeName}));}
  const stamp=sent.get(box.dataset.waStatus421+':'+status),text=stamp?'Enviado às '+stamp+' · confirme o envio no WhatsApp.':'';if(receipt.textContent!==text)receipt.textContent=text;
 });}
 root.addEventListener('click',event=>{const button=event.target.closest('[data-wa-send421]');if(!button||button.hidden)return;const box=button.closest('[data-wa-status421]');sent.set(box.dataset.waStatus421+':'+box.dataset.status421,new Date().toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit',timeZone:'America/Sao_Paulo'}));enhance();});
 new MutationObserver(enhance).observe(root,{childList:true,subtree:true});enhance();
})(typeof window!=='undefined'?window:globalThis);
