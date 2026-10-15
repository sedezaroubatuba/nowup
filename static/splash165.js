/* V181: bounded, decorative splash. Never blocks checkout or browser back. */
(()=>{'use strict';
 if(window.__nuSplash181)return;window.__nuSplash181=true;
 const start=()=>{
  if(matchMedia('(prefers-reduced-motion: reduce)').matches)return;
  if(location.pathname!=='/'&&!/^\/p\/[^/]+(?:\/menu)?\/?$/.test(location.pathname))return;
  const nav=performance.getEntriesByType?.('navigation')?.[0];if(nav?.type==='back_forward')return;
  try{if(sessionStorage.getItem('nowup-splash181'))return;sessionStorage.setItem('nowup-splash181','1');}catch(_){return;}
  const source=document.querySelector('.top .nowup-official-logo');if(!source)return;
  const splash=document.createElement('div');splash.className='nu165-splash nu165-home';splash.setAttribute('aria-hidden','true');splash.style.pointerEvents='none';
  const inner=document.createElement('div');inner.className='nu165-inner';const image=document.createElement('img');image.src=source.currentSrc||source.src;image.alt='';inner.append(image);splash.append(inner);
  const remove=()=>splash.remove();image.addEventListener('error',remove,{once:true});splash.addEventListener('animationend',e=>{if(e.target===splash)remove();});
  document.body.append(splash);setTimeout(remove,1500);window.addEventListener('pagehide',remove,{once:true});
 };
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
