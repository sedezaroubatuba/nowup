(()=>{'use strict';
 const el=document.getElementById('nowup-opening490');if(!el)return;
 const scope=el.dataset.openingScope,preview=el.dataset.openingPreview==='1';
 if(!['nowup','sede-zero'].includes(scope)){el.remove();return;}
 const key='nowup-opening-session490:'+scope;
 let first=true;try{first=sessionStorage.getItem(key)!=='1';sessionStorage.setItem(key,'1');}catch(_){try{first=!document.referrer||new URL(document.referrer).origin!==location.origin;}catch(_){first=true;}}
 if((!first&&!preview)||matchMedia('(prefers-reduced-motion: reduce)').matches){el.remove();return;}
 const video=el.querySelector('[data-opening-video]'),skip=el.querySelector('[data-opening-skip]');
 if(!video||!skip){el.remove();return;}
 let finished=false,startupTimer,hardTimer;
 const stop=()=>{if(finished)return;finished=true;clearTimeout(startupTimer);clearTimeout(hardTimer);document.removeEventListener('keydown',escape);document.removeEventListener('visibilitychange',visibility);window.removeEventListener('pagehide',stop);el.remove();try{video.pause();video.removeAttribute('src');video.load();}catch(_){}};
 const escape=e=>{if(e.key==='Escape')stop();};
 const visibility=()=>{if(document.hidden)stop();};
 skip.addEventListener('click',stop,{once:true});video.addEventListener('ended',stop,{once:true});video.addEventListener('error',stop,{once:true});
 video.addEventListener('playing',()=>clearTimeout(startupTimer),{once:true});
 document.addEventListener('keydown',escape);document.addEventListener('visibilitychange',visibility);window.addEventListener('pagehide',stop,{once:true});
 video.muted=true;video.defaultMuted=true;video.playsInline=true;video.preload='auto';
 video.poster=video.dataset.poster;video.src=video.dataset.src;
 el.hidden=false;
 // A slow connection or unsupported autoplay must never delay shopping.
 startupTimer=setTimeout(stop,1800);hardTimer=setTimeout(stop,5000);
 try{const p=video.play();if(p&&typeof p.catch==='function')p.catch(stop);}catch(_){stop();}
})();
