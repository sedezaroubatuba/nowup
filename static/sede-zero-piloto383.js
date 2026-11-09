/* One welcome per page entry; returning from checkout does not mount this dialog. */
(() => {
 'use strict';
 const dialog=document.getElementById('nu383-pilot');
 if(!dialog || typeof dialog.showModal!=='function')return;
 const image=dialog.querySelector('img'),close=dialog.querySelector('.nu383-close');
 const counter=dialog.querySelector('.nu383-countdown'),share=dialog.querySelector('.nu383-share');
 const status=dialog.querySelector('.nu383-status');
 let ready=false,timer,opened=false,previousFocus;
 const url=new URL(dialog.dataset.shareUrl,location.origin).href;
 function announce(message){status.textContent=message;status.hidden=false;}
 function dismiss(){if(ready)dialog.close();}
 function show(){
  if(opened || !image.naturalWidth)return;
  opened=true;previousFocus=document.activeElement;
  dialog.showModal();
  const deadline=performance.now()+3000;
  timer=setInterval(()=>{
   const remaining=Math.max(0,Math.ceil((deadline-performance.now())/1000));
   counter.textContent=String(remaining);
   if(remaining===0){ready=true;clearInterval(timer);counter.hidden=true;close.hidden=false;}
  },100);
 }
 close.addEventListener('click',dismiss);
 dialog.addEventListener('cancel',event=>{event.preventDefault();dismiss();});
 dialog.addEventListener('close',()=>{clearInterval(timer);if(previousFocus?.isConnected)previousFocus.focus();});
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
 window.addEventListener('pagehide',()=>{clearInterval(timer);if(dialog.open)dialog.close();},{once:true});
})();
