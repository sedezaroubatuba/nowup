(()=>{'use strict';
const root=document.getElementById('nu373-dialog');if(!root||typeof root.showModal!=='function')return;
const close=root.querySelector('[data-close373]'),title=root.querySelector('.nu373-title'),body=root.querySelector('.nu373-message'),link=root.querySelector('[data-link373]'),error=root.querySelector('[data-error373]');
let active=null,busy=false,closing=false,stopped=false,previous=null,restoreOverflow='',shown=false,timer;
const uid=root.dataset.userId,key=id=>'nowup-communication373:'+uid+':'+id;
function locallyClosed(id){try{return localStorage.getItem(key(id))==='closed'}catch{return false}}
function hide(){if(root.open)root.close();document.documentElement.style.overflow=restoreOverflow;active=null;previous?.focus?.();}
async function dismiss(){if(!active||closing)return;closing=true;close.disabled=true;error.hidden=true;
 const id=active.id;const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),8000);
 try{const r=await fetch('/painel/comunicacao/cards/'+id+'/fechar',{method:'POST',credentials:'same-origin',headers:{'X-Nowup-Notice':'373'},signal:controller.signal});if(!r.ok)throw Error('dismiss');}
 catch(_){/* Local persistence also prevents a repeated popup if the connection falls. */}
 finally{clearTimeout(timeout);try{localStorage.setItem(key(id),'closed')}catch{}hide();closing=false;close.disabled=false;}
}
close.addEventListener('click',dismiss);root.addEventListener('cancel',e=>{e.preventDefault();dismiss()});
function blocked(){const intro=document.getElementById('nowup-opening260');return Boolean((intro&&getComputedStyle(intro).display!=='none'&&getComputedStyle(intro).visibility!=='hidden')||document.querySelector('dialog[open]')||document.hidden)}
function show(notice){active=notice;shown=true;previous=document.activeElement;title.textContent=String(notice.title||'Mensagem NowUp');body.textContent=String(notice.message||'');link.hidden=true;error.hidden=true;
 if(notice.link&&notice.link!=='/painel'){try{const target=new URL(notice.link,location.origin);if(target.protocol==='https:'||(target.origin===location.origin&&target.pathname.startsWith('/painel'))){link.href=target.href;link.hidden=false}}catch{}}
 restoreOverflow=document.documentElement.style.overflow;document.documentElement.style.overflow='hidden';try{root.showModal();close.focus()}catch{document.documentElement.style.overflow=restoreOverflow;shown=false;active=null}
}
async function poll(){if(stopped||shown||busy)return;clearTimeout(timer);if(blocked()){timer=setTimeout(poll,1500);return}busy=true;const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),8000);
 try{const r=await fetch('/painel/comunicacao/cards',{credentials:'same-origin',cache:'no-store',signal:controller.signal});if(r.status===401||r.status===403){stopped=true;return}if(!r.ok)throw Error('feed');const data=await r.json();if(!Array.isArray(data.notices))return;const notices=data.notices.filter(n=>Number.isSafeInteger(n.id)&&n.id>0);for(const n of notices.filter(n=>locallyClosed(n.id))){fetch('/painel/comunicacao/cards/'+n.id+'/fechar',{method:'POST',credentials:'same-origin',headers:{'X-Nowup-Notice':'373'}}).catch(()=>{})}const next=notices.find(n=>!locallyClosed(n.id));if(next&&!blocked())show(next);
 }catch(_){}finally{clearTimeout(timeout);busy=false;if(!shown&&!stopped)timer=setTimeout(poll,15000)}
}
window.addEventListener('focus',poll);window.addEventListener('online',poll);document.addEventListener('visibilitychange',()=>{if(!document.hidden)poll()});window.addEventListener('storage',e=>{if(active&&e.key===key(active.id)&&e.newValue==='closed')hide()});poll();
})();
