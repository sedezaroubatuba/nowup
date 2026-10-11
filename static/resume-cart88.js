/* Show only the signed-in customer's unfinished carts on this device. */
(()=>{'use strict';
 const root=document.querySelector('[data-resume-carts][data-cart-user-id]');
 if(!root)return;
 const userId=root.dataset.cartUserId;
 if(!/^[1-9]\d*$/.test(userId))return;
 const prefix=`nowup-cart:u:${userId}:`,valid=/^(\/p\/[a-zA-Z0-9_-]+)(?:\/menu)?$/;
 const money=c=>(c/100).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
 function readCarts(storage){
  const grouped=new Map();
  for(let i=0;i<storage.length;i++){
   const key=storage.key(i);if(!key?.startsWith(prefix))continue;
   const match=key.slice(prefix.length).match(valid);if(!match)continue;
   try{const values=JSON.parse(storage.getItem(key));if(!Array.isArray(values))continue;
    let count=0,sum=0;
    for(const entry of values){if(!Array.isArray(entry)||!entry[1])continue;const v=entry[1],q=Number(v.quantity),price=Number(v.unitPrice??v.price);if(!Number.isInteger(q)||q<1||q>99||!Number.isFinite(price)||price<0)continue;count+=q;sum+=q*price;}
    if(!count)continue;
    const path=match[1],existing=grouped.get(path);if(existing&&existing.key===prefix+path)continue;
    let info={};try{info=JSON.parse(storage.getItem(`nowup-cart-info:u:${userId}:${path}`)||'{}')||{};}catch(_){}
    grouped.set(path,{key,path,count,sum,name:String(info.name||path.slice(3).replace(/-/g,' ')),updated:Number(info.updated)||0});
   }catch(_){}
  }
  return [...grouped.values()].sort((a,b)=>b.updated-a.updated);
 }
 function clearCompleted(){const raw=document.cookie.split('; ').find(x=>x.startsWith('nowup_cart_completed='));if(!raw)return;
  try{const slug=decodeURIComponent(raw.split('=').slice(1).join('='));if(/^[a-zA-Z0-9_-]+$/.test(slug)){const path='/p/'+slug;localStorage.removeItem(prefix+path);localStorage.removeItem(prefix+path+'/menu');localStorage.removeItem(`nowup-cart-info:u:${userId}:${path}`);}}catch(_){}
  document.cookie='nowup_cart_completed=; Max-Age=0; Path=/; SameSite=Lax';
 }
 function render(){
  let carts=[];try{carts=readCarts(localStorage);}catch(_){}
  const current=location.pathname.replace(/\/menu\/?$/,'').replace(/\/$/,'');carts=carts.filter(c=>c.path!==current);
  root.replaceChildren();root.hidden=!carts.length;if(!carts.length)return;
  const heading=document.createElement('strong');heading.textContent='🛒 Você tem um pedido em andamento';root.append(heading);
  for(const c of carts){const link=document.createElement('a');link.href=c.path+'#nu83-cart';link.className='nu88-cart-link';link.setAttribute('aria-label','Continuar pedido em '+c.name);
   const title=document.createElement('span');title.textContent=c.name+' · '+c.count+(c.count===1?' item':' itens');
   const action=document.createElement('b');action.textContent='Continuar · '+money(c.sum);link.append(title,action);root.append(link);}
  const header=document.querySelector('.top');root.style.setProperty('--nu88-header-height',Math.max(0,header?.getBoundingClientRect().height||0)+'px');
 }
 const init=()=>{clearCompleted();render();window.addEventListener('nowup-cart-changed',render);window.addEventListener('storage',render);window.addEventListener('pageshow',render);};
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
