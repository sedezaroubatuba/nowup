/* Fixed portions: kilograms + grams. Server recalculates all prices independently. */
function weightTotal370(rate,kg,g){
 if(![rate,kg,g].every(Number.isSafeInteger)||rate<1||rate>10000000||kg<0||kg>99||g<0||g>900||g%100)throw Error('Peso inválido');
 const grams=kg*1000+g;if(grams<100||grams>99900)throw Error('Escolha pelo menos 100 g');
 return {grams,cents:Math.floor((rate*grams+500)/1000)};
}
if(typeof module!=='undefined')module.exports={weightTotal370};
if(typeof document!=='undefined')document.addEventListener('DOMContentLoaded',()=>{
 const root=document.querySelector('[data-native-menu]');if(!root)return;
 const cards=()=>[...root.querySelectorAll('[data-product]')];
 const dialog=document.createElement('dialog');dialog.className='nu370-dialog';dialog.setAttribute('aria-labelledby','nu370-title');
 dialog.innerHTML='<header><h2 id="nu370-title"></h2><button type="button" data-close370 aria-label="Fechar produto">×</button></header><img alt=""><p class="nu370-rate"></p><label>Quilos<select aria-label="Quilos" data-kg370></select></label><label>Gramas<select aria-label="Gramas" data-g370></select></label><p data-weight-label370 aria-live="polite"></p><p class="nu370-total" aria-live="polite"></p><p class="nu370-notice">Você paga pelo peso escolhido. Se a loja enviar um pouco a mais, não haverá cobrança extra.</p><p data-error370 role="alert"></p><button type="button" class="btn primary" data-save370></button>';
 document.body.append(dialog);
 const kg=dialog.querySelector('[data-kg370]'),g=dialog.querySelector('[data-g370]'),button=dialog.querySelector('[data-save370]'),error=dialog.querySelector('[data-error370]');let card=null,returnTo=null,previousFocus=null;
 for(let n=0;n<=99;n++)kg.add(new Option(n+' kg',String(n)));
 for(let n=0;n<=900;n+=100)g.add(new Option(n+' g',String(n)));
 const money=c=>(c/100).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
 function update(){try{const value=weightTotal370(Number(card.dataset.price),Number(kg.value),Number(g.value));dialog.querySelector('[data-weight-label370]').textContent='Peso total: '+(value.grams/1000).toLocaleString('pt-BR')+' kg ('+value.grams.toLocaleString('pt-BR')+' g)';dialog.querySelector('.nu370-total').textContent='Total: '+money(value.cents);button.textContent='Adicionar • '+money(value.cents);button.disabled=false;error.textContent='';}catch(e){button.disabled=true;error.textContent=e.message;dialog.querySelector('[data-weight-label370]').textContent='';dialog.querySelector('.nu370-total').textContent='';button.textContent='Escolha o peso';}}
 function open(source){
  if(!source||source.dataset.weight370!=='1'||source.querySelector('[data-add]')?.disabled)return;
  if(!window.NOWUP_CART160){const buy=source.querySelector('[data-add]');buy?.click();return;}
  card=source;previousFocus=document.activeElement;returnTo=document.querySelector('dialog[open]');if(returnTo&&returnTo!==dialog)returnTo.close();
  dialog.querySelector('h2').textContent=card.dataset.name;
  dialog.querySelector('.nu370-rate').textContent=money(Number(card.dataset.price))+'/kg';
  const img=dialog.querySelector('img'),photo=card.querySelector('img'),src=photo?.dataset.src258||photo?.getAttribute('src')||'';img.hidden=!src||src.includes('placeholder');if(!img.hidden){img.src=src;img.alt=card.dataset.name;}
  const grams=window.NOWUP_CART160.weight(card.dataset.id)||100;kg.value=String(Math.floor(grams/1000));g.value=String(grams%1000);update();
  if(!dialog.open)dialog.showModal();kg.focus();
 }
 window.NOWUP_WEIGHT370={open};kg.addEventListener('change',update);g.addEventListener('change',update);
 button.addEventListener('click',()=>{try{const value=weightTotal370(Number(card.dataset.price),Number(kg.value),Number(g.value));window.NOWUP_CART160.setWeight(card,value.grams);dialog.close();}catch(e){error.textContent=e.message;}});
 dialog.querySelector('[data-close370]').addEventListener('click',()=>dialog.close());
 dialog.addEventListener('close',()=>{if(returnTo?.isConnected&&!returnTo.open)returnTo.showModal();previousFocus?.focus?.();returnTo=null;});
 // Capture product-card clicks before unit selectors. Authentication remains owned by store-app256.
 document.addEventListener('click',e=>{
  if(e.target.closest('.nu370-dialog'))return;
  const edit=e.target.closest('[data-edit-weight370]');
  const source=e.target.closest('[data-source256]'),native=e.target.closest('[data-product]');
  const product=edit?cards().find(c=>c.dataset.id===edit.dataset.editWeight370):native||cards().find(c=>c.dataset.id===source?.dataset.source256);
  if(product?.dataset.weight370!=='1'||!window.NOWUP_CART160||e.target.closest('[data-remove]'))return;
  e.preventDefault();e.stopImmediatePropagation();open(product);
 },true);
});
