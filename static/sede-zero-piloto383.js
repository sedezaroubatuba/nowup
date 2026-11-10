/* At most two dismissible appearances per rolling 24 hours on this browser. */
(() => {
 'use strict';
 const dialog=document.getElementById('nu383-pilot');
 if(!dialog || typeof dialog.showModal!=='function')return;
 const image=dialog.querySelector('img'),close=dialog.querySelector('.nu383-close');
 const share=dialog.querySelector('.nu383-share');
 const status=dialog.querySelector('.nu383-status');
 let opened=false,previousFocus;
 const storageKey='nowup-sede-zero-share400',windowMs=24*60*60*1000;
 function reserveShowing(){
  const now=Date.now();
  for(const name of ['localStorage','sessionStorage']){
   try{const storage=window[name];if(!storage)continue;const raw=JSON.parse(storage.getItem(storageKey)||'[]');const shown=(Array.isArray(raw)?raw:[]).filter(t=>Number.isFinite(t)&&t<=now&&now-t<windowMs);
    if(shown.length>=2)return false;shown.push(now);storage.setItem(storageKey,JSON.stringify(shown));return true;
   }catch(_){}
  }
  return false; // Avoid repeated prompts when the browser blocks all storage.
 }
 const url=new URL(dialog.dataset.shareUrl,location.origin).href;
 function announce(message){status.textContent=message;status.hidden=false;}
 function dismiss(){dialog.close();}
 function show(){
  if(opened || !image.naturalWidth)return;
  if(!reserveShowing())return;
  opened=true;previousFocus=document.activeElement;
  close.hidden=false;
  dialog.showModal();
 }
 close.addEventListener('click',dismiss);
 dialog.addEventListener('cancel',event=>{event.preventDefault();dismiss();});
 dialog.addEventListener('close',()=>{if(previousFocus?.isConnected)previousFocus.focus();});
 share.addEventListener('click',async()=>{
  const data={title:'Cardápio da Adega Sede Zero',text:'Confira o cardápio da Sede Zero no NowUp e compartilhe com os amigos!',url};
  if(navigator.share){
   try{await navigator.share(data);return;}
   catch(error){if(error.name==='AbortError')return;}
  }
  if(navigator.clipboard?.writeText){
   try{await navigator.clipboard.writeText(url);announce('Link copiado! Cole na conversa com seus amigos.');return;}catch(error){}
  }
  announce('Copie e compartilhe este link: '+url);
 });
 if(image.complete)show();else image.addEventListener('load',show,{once:true});
 window.addEventListener('pagehide',()=>{if(dialog.open)dialog.close();},{once:true});
})();
