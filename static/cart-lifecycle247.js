/* Reconcile only a submitted snapshot after authenticated server confirmation. */
(()=>{'use strict';
 const pendingPrefix='nowup-checkout247:';
 function read(storage,key){try{return JSON.parse(storage.getItem(key)||'null');}catch(_){return null;}}
 function forget(key){try{sessionStorage.removeItem(pendingPrefix+key);}catch(_){}}
 function prepare(key,payload,snapshot){
  const old=read(sessionStorage,pendingPrefix+key);
  const token=old&&old.payload===payload&&old.snapshot===snapshot&&Date.now()-old.time<86400000?old.token:crypto.randomUUID();
  try{sessionStorage.setItem(pendingPrefix+key,JSON.stringify({token,payload,snapshot,time:Date.now()}));}catch(_){}
  return token;
 }
 function complete(key,pending){
  // Never erase a different/new cart or another account/store.
  if(localStorage.getItem(key)!==pending.snapshot)return false;
  localStorage.removeItem(key);localStorage.removeItem(key.replace('nowup-cart:','nowup-cart-info:'));
  forget(key);window.dispatchEvent(new CustomEvent('nowup-cart-confirmed247',{detail:{key}}));
  window.dispatchEvent(new Event('nowup-cart-changed'));return true;
 }
 let running=false;
 async function reconcile(){
  if(running)return;running=true;
  try{
   const keys=[];for(let i=0;i<sessionStorage.length;i++){const k=sessionStorage.key(i);if(k?.startsWith(pendingPrefix))keys.push(k);}
   for(const full of keys){
    const key=full.slice(pendingPrefix.length),match=key.match(/^nowup-cart:u:([1-9]\d*):(\/p\/[a-zA-Z0-9_-]+)$/),pending=read(sessionStorage,full);
    if(!match||!pending||Date.now()-pending.time>86400000){forget(key);continue;}
    const response=await fetch('/api/cart-completion247?request_key='+encodeURIComponent(pending.token),{credentials:'same-origin',cache:'no-store'});
    if(!response.ok)continue;
    const result=await response.json();if(result.confirmed&&result.path===match[2]){complete(key,pending);forget(key);}
   }
  }catch(_){}finally{running=false;}
 }
 window.NOWUP_CHECKOUT247={prepare,reconcile};
 window.addEventListener('pageshow',reconcile);
 document.addEventListener('visibilitychange',()=>{if(!document.hidden)reconcile();});
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',reconcile,{once:true});else reconcile();
})();
