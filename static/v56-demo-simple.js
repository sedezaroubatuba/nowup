/* V181: file preview and size/type checks. Server validation stays authoritative. */
(()=>{'use strict';
 const start=()=>{
  const form=document.getElementById('demo-simple-form');if(!form||form.dataset.preview181)return;form.dataset.preview181='1';
  const error=document.getElementById('demo-photo-error'),urls=new Map(),allowed=new Set(['image/jpeg','image/png','image/webp']);
  function release(input){const old=urls.get(input);if(old){URL.revokeObjectURL(old);urls.delete(input);}}
  function check(input){release(input);const preview=form.querySelector('[data-demo-preview="'+input.name+'"]');if(preview){preview.hidden=true;preview.removeAttribute('src');}input.setCustomValidity('');const file=input.files?.[0];if(!file)return true;
   let message='';if(!allowed.has(file.type))message='Use uma imagem JPG, PNG ou WebP.';else if(file.size>5*1024*1024)message='A imagem deve ter no máximo 5 MB.';
   if(message){input.setCustomValidity(message);return false;}
   if(preview){const url=URL.createObjectURL(file);urls.set(input,url);preview.src=url;preview.hidden=false;preview.onerror=()=>{preview.hidden=true;};}return true;
  }
  function show(){const invalid=[...form.querySelectorAll('[data-simple-upload]')].find(input=>input.validity.customError);if(error){error.hidden=!invalid;error.textContent=invalid?.validationMessage||'';}}
  form.querySelectorAll('[data-simple-upload]').forEach(input=>input.addEventListener('change',()=>{check(input);show();}));
  form.addEventListener('submit',event=>{if(!form.checkValidity()){event.preventDefault();form.reportValidity();show();}});
  window.addEventListener('pagehide',()=>{urls.forEach(url=>URL.revokeObjectURL(url));urls.clear();});
 };
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
