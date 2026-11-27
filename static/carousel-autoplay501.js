/* Mobile-only autoplay for single-item promotional carousels. */
(() => {
 'use strict';
 const mobile=matchMedia('(max-width:900px) and (pointer:coarse)');
 const reduced=matchMedia('(prefers-reduced-motion: reduce)');
 function attach({track,controls=track,advance,enabled=()=>true}){
  if(!track||typeof advance!=='function')return;
  let pausedUntil=0,pressed=false,visible=false;
  const postpone=()=>{pausedUntil=Date.now()+6000;};
  const observer=typeof IntersectionObserver==='function'?new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;},{threshold:0.15}):null;
  if(observer)observer.observe(track);else visible=true;
  controls.addEventListener('pointerdown',()=>{pressed=true;postpone();},{passive:true});
  const release=()=>{if(pressed){pressed=false;postpone();}};
  window.addEventListener('pointerup',release,{passive:true});
  window.addEventListener('pointercancel',release,{passive:true});
  controls.addEventListener('touchstart',postpone,{passive:true});
  controls.addEventListener('touchend',postpone,{passive:true});
  controls.addEventListener('wheel',postpone,{passive:true});
  controls.addEventListener('keydown',postpone);
  controls.addEventListener('click',postpone);
  controls.addEventListener('nu501-manual',postpone);
  const timer=setInterval(()=>{
   if(!track.isConnected){clearInterval(timer);observer?.disconnect();window.removeEventListener('pointerup',release);window.removeEventListener('pointercancel',release);return;}
   if(!mobile.matches||reduced.matches||document.hidden||!visible||pressed||Date.now()<pausedUntil||!enabled())return;
   if(!track.getClientRects().length||track.scrollWidth-track.clientWidth<3||document.querySelector('dialog[open]'))return;
   if(controls.contains(document.activeElement)&&document.activeElement?.matches(':focus-visible'))return;
   advance();
  },2000);
 }
 window.NowUpAutoSlide501={attach};
})();
