/* One-shot page peel only after a server-confirmed order. No checkout/payment side effects. */
(()=>{'use strict';
 const key='nowup-order-turn368';let timer=null,frame=null,layer=null;
 const reduced=()=>window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
 function target(url){try{const u=new URL(url,location.href);return u.origin===location.origin&&/^\/(?:p\/[A-Za-z0-9_-]+\/)?pedido\/[A-Za-z0-9_-]+$/.test(u.pathname)?u.pathname:null;}catch(_){return null;}}
 function prepare(url){const path=target(url);if(!path)return;try{sessionStorage.setItem(key,JSON.stringify({path,at:Date.now()}));}catch(_){} }
 function remove(){clearTimeout(timer);if(frame!==null)cancelAnimationFrame(frame);frame=null;layer?.remove();layer=null;}
 function play(){
  remove();if(reduced())return;
  const art=document.querySelector('#nu368-rider-art');if(!art)return;
  layer=document.createElement('div');layer.id='nu368-turn';layer.setAttribute('aria-hidden','true');layer.setAttribute('popover','manual');
  layer.innerHTML='<div class="nu368-sheet"><div class="nu368-paper"><div class="nu368-paper-top"><span>←</span><b>Finalizar pedido</b><span>☰</span></div><div class="nu368-paper-content"><h2>Seu pedido</h2><div class="nu368-summary"></div><div class="nu368-skeleton"></div><div class="nu368-skeleton short"></div><div class="nu368-send">Enviando pedido…</div></div></div><div class="nu368-curl"></div></div><div class="nu368-tow"><span class="nu368-rope"></span><div class="nu368-rider"></div></div>';
  // Copy only existing order line labels and totals, as text; never persist personal data.
  const summary=layer.querySelector('.nu368-summary'),lines=document.querySelectorAll('.order-track .nu347-item-title h3, [data-whatsapp-ready257] pre');
  [...lines].slice(0,4).forEach(n=>{const line=document.createElement('p');line.textContent=n.textContent.slice(0,140);summary.append(line);});
  const total=document.querySelector('.nu347-grand-total strong');if(total){const p=document.createElement('strong');p.textContent='Total: '+total.textContent;summary.append(p);}
  layer.querySelector('.nu368-rider').append(art.content.cloneNode(true));
  document.body.append(layer);try{if(layer.showPopover)layer.showPopover();else (document.querySelector('dialog[open]')||document.body).append(layer);}catch(_){}
  frame=requestAnimationFrame(()=>{frame=null;if(!layer)return;layer.classList.add('nu368-playing');});
  timer=setTimeout(remove,2400);
 }
 window.NOWUP_ORDER_TURN368={prepare,reveal:play};
 if(document.querySelector('.order-track')){let pending=null;try{pending=JSON.parse(sessionStorage.getItem(key));sessionStorage.removeItem(key);}catch(_){}if(pending&&pending.path===location.pathname&&Date.now()-pending.at>=0&&Date.now()-pending.at<90000)play();}
 window.addEventListener('pagehide',remove);window.addEventListener('pageshow',event=>{if(event.persisted)remove();});
})();
