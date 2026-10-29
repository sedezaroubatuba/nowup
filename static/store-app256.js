(()=>{'use strict';
 const configNode=document.getElementById('store-app256');if(!configNode)return;
 const cfg=JSON.parse(configNode.textContent);let deferred=null,installedHere=false;
 if(configNode.dataset.loginRequired==='1'){
  document.addEventListener('click',e=>{const b=e.target.closest?.('[data-add],[data-login-buy252],.nu201-open,.nu190-add,.nu151-choose,[data-checkout],[data-dock-checkout],[data-cart-summary]');if(b&&b.closest('[data-native-menu]')&&!b.disabled){e.preventDefault();e.stopImmediatePropagation();location.assign(cfg.login);}},true);
 }
 const installed=()=>installedHere||matchMedia('(display-mode: standalone)').matches||navigator.standalone===true;
 const buttons=[...document.querySelectorAll('[data-store-install256]')];
 function refresh(){buttons.forEach(b=>b.hidden=installed());}
 window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();deferred=e;refresh();});
 window.addEventListener('appinstalled',()=>{installedHere=true;deferred=null;refresh();});
 buttons.forEach(b=>b.addEventListener('click',async()=>{
  if(deferred){const prompt=deferred;deferred=null;await prompt.prompt();await prompt.userChoice;refresh();return;}
  const dialog=document.getElementById('store-install-help256');if(dialog&&!dialog.open)dialog.showModal();
 }));
 document.querySelectorAll('[data-store-share256]').forEach(b=>b.addEventListener('click',async()=>{
  const url=new URL(cfg.menu,location.origin).href;
  try{if(navigator.share)await navigator.share({title:cfg.name,text:'Veja o cardápio de '+cfg.name,url});else{await navigator.clipboard.writeText(url);b.textContent='Link copiado';}}catch(e){if(e.name!=='AbortError'){const box=document.getElementById('store-share-url256');box.hidden=false;box.value=url;box.select();}}
 }));
 if(isSecureContext&&'serviceWorker' in navigator)navigator.serviceWorker.register('/nowup-push-sw.js',{scope:'/',updateViaCache:'none'}).catch(()=>{});
 refresh();
})();
