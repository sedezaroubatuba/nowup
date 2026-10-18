/* Customer-owned order summaries, independent of push permission. */
(()=>{'use strict';
 const host=document.getElementById('nu202-orders');if(!host||!document.body.classList.contains('v50-directory-home'))return;
 const body=document.body,key='nowup-order-dismiss202:'+host.dataset.customer202;
 let dismissed=new Set();try{dismissed=new Set(JSON.parse(sessionStorage.getItem(key)||'[]'));}catch(_){}
 let timer,busy=false,stopped=false,signature='',last=[],expanded=false;
 const make=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;};
 function measure(){body.style.setProperty('--nu202-height',host.hidden?'0px':Math.ceil(host.getBoundingClientRect().height)+'px');}
 function render(orders){
  last=orders;const visible=orders.filter(o=>o.active||!dismissed.has(String(o.id)+':'+o.status));
  const next=JSON.stringify(visible);if(next===signature)return;signature=next;
  host.replaceChildren();host.hidden=!visible.length;body.classList.toggle('nu202-has-orders',!!visible.length);
  if(!visible.length){measure();return;}
  const wrap=make('div','nu202-wrap'),active=visible.filter(o=>o.active);
  function row(o){
   const box=make('div','nu202-row'),link=make('a','nu202-link');link.href=o.url;
   const icon=make('span','nu202-icon','♧');icon.textContent=o.status==='out_for_delivery'?'🛵':'🛍';icon.setAttribute('aria-hidden','true');
   const copy=make('span','nu202-copy');copy.append(make('strong','',o.label),make('small','',o.store+' · Pedido '+o.code),make('span','nu202-action','Acompanhar pedido ›'));link.append(icon,copy);box.append(link);
   if(!o.active){const close=make('button','nu202-dismiss','×');close.type='button';close.setAttribute('aria-label','Dispensar aviso do pedido '+o.code);close.addEventListener('click',()=>{dismissed.add(String(o.id)+':'+o.status);try{sessionStorage.setItem(key,JSON.stringify([...dismissed]));}catch(_){}signature='';render(last);});box.append(close);}
   return box;
  }
  const live=make('span','nu202-sr',active.length>1?active.length+' pedidos em andamento':visible[0].label);live.setAttribute('role','status');live.setAttribute('aria-live','polite');wrap.append(live,row(visible[0]));
  if(visible.length>1){const more=make('details','nu202-more'),summary=make('summary','',active.length>1?'Você tem '+active.length+' pedidos em andamento':'Ver outros pedidos ('+(visible.length-1)+')');more.open=expanded;more.append(summary);const list=make('div','nu202-list');visible.slice(1).forEach(o=>list.append(row(o)));more.append(list);more.addEventListener('toggle',()=>{expanded=more.open;measure();});wrap.append(more);}
  const warning=make('small','nu202-warning');warning.hidden=true;wrap.append(warning);host.append(wrap);measure();
 }
 function schedule(){clearTimeout(timer);if(!stopped)timer=setTimeout(poll,10000);}
 async function poll(){
  clearTimeout(timer);if(stopped)return;if(busy)return;if(document.hidden){schedule();return;}busy=true;
  const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),8000);
  try{const response=await fetch('/cliente/pedidos/resumo202',{credentials:'same-origin',cache:'no-store',signal:controller.signal});
   if(response.status===401||response.status===403){stopped=true;host.hidden=true;body.classList.remove('nu202-has-orders');measure();return;}
   if(!response.ok)throw Error('fetch');const data=await response.json();if(!Array.isArray(data.orders))throw Error('data');
   render(data.orders);const warning=host.querySelector('.nu202-warning');if(warning)warning.hidden=true;
  }catch(_){const warning=host.querySelector('.nu202-warning');if(warning){warning.textContent='Não foi possível atualizar agora. Tentando novamente…';warning.hidden=false;measure();}}
  finally{clearTimeout(timeout);busy=false;schedule();}
 }
 if(window.ResizeObserver)new ResizeObserver(measure).observe(host);
 window.addEventListener('resize',measure);window.addEventListener('online',poll);window.addEventListener('focus',poll);document.addEventListener('visibilitychange',()=>{if(!document.hidden)poll();});window.addEventListener('pageshow',poll);poll();
})();
