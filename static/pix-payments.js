(()=>{'use strict';
  function attach(host,pix){
    if(!pix||typeof pix.payload!=='string'||!/^000201/.test(pix.payload)||!/^data:image\/png;base64,/.test(pix.qr_image||''))return;
    const section=document.createElement('section');section.style.cssText='padding:18px;border:1px solid #dfd0ed;border-radius:16px;background:#fff;margin:16px 0;color:#241a31';
    const title=document.createElement('h3');title.textContent='Pagar com Pix';section.append(title);
    const amount=document.createElement('p');amount.textContent='Valor: '+pix.amount+' • Recebedor informado: '+pix.receiver;section.append(amount);
    const img=document.createElement('img');img.src=pix.qr_image;img.alt='QR Code Pix com o valor do pedido';img.style.cssText='display:block;width:270px;max-width:100%;height:auto;margin:12px auto';section.append(img);
    const label=document.createElement('label');label.textContent='Pix Copia e Cola';
    const value=document.createElement('textarea');value.readOnly=true;value.value=pix.payload;value.rows=4;value.style.cssText='width:100%;box-sizing:border-box;font:13px monospace;word-break:break-all';label.append(value);section.append(label);
    const status=document.createElement('p');status.setAttribute('role','status');
    const button=document.createElement('button');button.type='button';button.className='btn primary full-btn';button.textContent='Copiar código Pix';
    button.addEventListener('click',async()=>{try{await navigator.clipboard.writeText(pix.payload);status.textContent='Código Pix copiado.';}catch(_){value.focus();value.select();status.textContent='Selecione e copie o código acima para colar no seu banco.';}});section.append(button,status);
    const note=document.createElement('p');note.textContent='Confira o favorecido no aplicativo do banco. '+pix.confirmation;section.append(note);host.append(section);
  }
  window.NOWUP_PIX={attach};
  function init(){document.querySelectorAll('[data-pix-payment]').forEach(host=>{if(host.dataset.pixReady)return;host.dataset.pixReady='1';try{attach(host,JSON.parse(host.querySelector('script[type="application/json"]').textContent));}catch(_){}});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
