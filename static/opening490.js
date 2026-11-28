(()=>{'use strict';
 const el=document.getElementById('nowup-opening490');if(!el)return;
 const scope=el.dataset.openingScope,preview=el.dataset.openingPreview==='1';
 if(!['nowup','sede-zero'].includes(scope)){el.remove();return;}
 // V527: one shared rolling quota across the two openings, per browser/device.
 const key='nowup-opening-rolling527',windowMs=86400000,maximum=3;
 const entryScope=path=>{const parts=path.replace(/\/$/,'').split('/');return parts[1]==='p'&&['adega-sede-zero','samuel-dos-santos-silva'].includes(parts[2])?'sede-zero':parts[1]===''?'nowup':'';};
 const eligible=()=>{
  if(preview)return true;
  const nav=performance.getEntriesByType('navigation')[0];
  if(nav&&['reload','back_forward'].includes(nav.type))return false;
  try{
   if(document.referrer){const ref=new URL(document.referrer);if(ref.origin===location.origin){
    if(scope==='nowup'||entryScope(ref.pathname)===scope)return false;
   }}
  }catch(_){return false;}
  return true;
 };
 const history=()=>{const now=Date.now();const value=JSON.parse(localStorage.getItem(key)||'[]');return (Array.isArray(value)?value:[]).filter(t=>Number.isFinite(t)&&t>now-windowMs&&t<=now);};
 const allowed=()=>{if(preview)return true;try{return history().length<maximum;}catch(_){return false;}};
 const record=()=>{if(preview)return true;try{const recent=history();if(recent.length>=maximum)return false;recent.push(Date.now());localStorage.setItem(key,JSON.stringify(recent));return true;}catch(_){return false;}};
 if(!eligible()||!allowed()||matchMedia('(prefers-reduced-motion: reduce)').matches){el.remove();return;}
 const video=el.querySelector('[data-opening-video]'),skip=el.querySelector('[data-opening-skip]');
 if(!video||!skip){el.remove();return;}
 let finished=false,startupTimer,hardTimer;
 const stop=()=>{if(finished)return;finished=true;clearTimeout(startupTimer);clearTimeout(hardTimer);document.removeEventListener('keydown',escape);document.removeEventListener('visibilitychange',visibility);window.removeEventListener('pagehide',stop);el.remove();try{video.pause();video.removeAttribute('src');video.load();}catch(_){}};
 const escape=e=>{if(e.key==='Escape')stop();};
 const visibility=()=>{if(document.hidden)stop();};
 skip.addEventListener('click',stop,{once:true});video.addEventListener('ended',stop,{once:true});video.addEventListener('error',stop,{once:true});
 video.addEventListener('playing',()=>{if(finished)return;if(!record()){stop();return;}clearTimeout(startupTimer);el.classList.remove('opening490-loading');},{once:true});
 document.addEventListener('keydown',escape);document.addEventListener('visibilitychange',visibility);window.addEventListener('pagehide',stop,{once:true});
 video.muted=true;video.defaultMuted=true;video.playsInline=true;video.preload='auto';
 el.classList.add('opening490-loading');el.hidden=false;
 video.removeAttribute('poster');video.src=video.dataset.src;
 // A slow connection or unsupported autoplay must never delay shopping.
 startupTimer=setTimeout(stop,1800);hardTimer=setTimeout(stop,5000);
 try{const p=video.play();if(p&&typeof p.catch==='function')p.catch(stop);}catch(_){stop();}
})();
