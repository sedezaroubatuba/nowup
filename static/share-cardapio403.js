(()=>{'use strict';
const match=location.pathname.match(/^\/p\/([^/]+)(?:\/menu)?\/?$/);if(!match)return;
async function share(){
 const node=document.getElementById('store-app256');let cfg=null;try{cfg=JSON.parse(node?.textContent||'null')}catch(_){}
 const url=new URL(cfg?.menu||('/p/'+match[1]+'/menu'),location.origin).href;
 const data={title:cfg?.name||'Cardápio da Sede Zero',text:'Confira o cardápio e compartilhe com os amigos!',url};
 if(navigator.share){try{await navigator.share(data);return}catch(e){if(e.name==='AbortError')return}}
 let copied=false;try{await navigator.clipboard.writeText(url);copied=true}catch(_){}
 let box=document.getElementById('nu403-share');if(!box){box=document.createElement('dialog');box.id='nu403-share';box.style.cssText='max-width:90vw;width:420px;border:1px solid #d9c9e7;border-radius:18px;padding:24px;color:#352444';document.body.append(box)}
 box.replaceChildren();const title=document.createElement('h2');title.textContent=copied?'Link copiado!':'Compartilhe o cardápio';const text=document.createElement('p');text.textContent=copied?'Cole o link no WhatsApp ou envie para seus amigos.':'Copie o link abaixo para enviar aos seus amigos.';
 const input=document.createElement('input');input.value=url;input.readOnly=true;input.setAttribute('aria-label','Link do cardápio');input.style.cssText='width:100%;box-sizing:border-box;padding:12px';input.addEventListener('click',()=>input.select());const close=document.createElement('button');close.type='button';close.className='btn primary';close.textContent='Fechar';close.onclick=()=>box.close();box.append(title,text,input,close);box.showModal();
}
document.addEventListener('nowup-share-cardapio403',share);
})();
