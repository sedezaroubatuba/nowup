/* Compact controls reuse the existing sound engine; hiding options never stops polling. */
(()=>{'use strict';
 const sound=document.getElementById('merchant-sound427'),stock=document.getElementById('stock-reminder427'),bell=document.querySelector('[data-sound-home427]');
 const top=document.querySelector('.v60-top'),menu=top?.querySelector('[data-pro-menu-toggle]');
 if(bell){bell.innerHTML='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/></svg>';if(menu)menu.after(bell);else document.querySelector('.top .nav,.topbar .nav')?.append(bell);}
 function open(dialog){if(!dialog||dialog.open)return;for(const other of [sound,stock])if(other?.open)other.close();dialog.showModal();}
 document.addEventListener('click',event=>{const target=event.target.closest('button,a');if(!target)return;
 if(target.matches('[data-open-sound427]'))open(sound);
 if(target.matches('[data-open-stock427]'))open(stock);
 if(target.matches('[data-close427]'))target.closest('dialog')?.close();
 if(target.matches('[data-close-link427]'))target.closest('dialog')?.close();
 });
 for(const dialog of [sound,stock])if(dialog){dialog.addEventListener('click',event=>{if(event.target!==dialog)return;const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();});}
 const messages=document.getElementById('nu203-alerts');if(sound&&messages){const extra=document.createElement('details'),title=document.createElement('summary');title.textContent='Som das mensagens';extra.append(title,messages);sound.append(extra);}
 const engine=sound?.querySelector('[data-order-alerts]');if(engine&&bell){const sync=()=>{bell.dataset.soundState=engine.dataset.soundState||'inactive';bell.setAttribute('aria-label',engine.dataset.soundState==='active'?'Som dos pedidos: campainha ativada':'Som dos pedidos: ativar campainha');};new MutationObserver(sync).observe(engine,{attributes:true,attributeFilter:['data-sound-state']});sync();}
 if(stock){const key='nowup-stock-reminder427:'+stock.dataset.merchant427;stock.addEventListener('close',()=>{try{sessionStorage.setItem(key,'dismissed');}catch(_){}});let dismissed=false;try{dismissed=sessionStorage.getItem(key)==='dismissed';}catch(_){}
 const detail=new URL(location.href).searchParams.has('abrir_pedido');if(!dismissed&&!detail&&['','#inicio','#pedidos-ativos'].includes(location.hash))open(stock);
 }
})();
