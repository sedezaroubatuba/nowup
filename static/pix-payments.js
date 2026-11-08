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
    const note=document.createElement('p');note.textContent='Confira o favorecido no aplicativo do banco. '+pix.confirmation;section.append(note);
    const proofBox=document.createElement('div');proofBox.style.cssText='margin-top:18px;padding-top:16px;border-top:1px solid #dfd0ed';
    const proofLabel=document.createElement('label');proofLabel.textContent='Anexar comprovante do Pix';
    const input=document.createElement('input');input.type='file';input.accept='image/jpeg,image/png,image/webp,application/pdf';input.style.cssText='display:block;max-width:100%;margin:10px 0';proofLabel.append(input);proofBox.append(proofLabel);
    const proofStatus=document.createElement('p');proofStatus.setAttribute('role','status');proofStatus.textContent='Depois de pagar, escolha a imagem ou o PDF do comprovante (até 10 MB).';
    const send=document.createElement('button');send.type='button';send.className='btn primary full-btn';send.textContent='Enviar comprovante pelo WhatsApp';send.hidden=true;
    const remove=document.createElement('button');remove.type='button';remove.className='btn soft';remove.textContent='Remover comprovante';remove.hidden=true;
    let proof=null;
    input.addEventListener('change',()=>{
      proof=null;send.hidden=true;remove.hidden=true;
      const file=input.files?.[0];if(!file){proofStatus.textContent='Nenhum comprovante selecionado.';return;}
      const allowed=['image/jpeg','image/png','image/webp','application/pdf'];
      if(file.size===0||file.size>10*1024*1024||!(allowed.includes(file.type)||(!file.type&&/\.(jpe?g|png|webp|pdf)$/i.test(file.name)))){input.value='';proofStatus.textContent='Escolha uma imagem JPG, PNG, WebP ou PDF de até 10 MB.';return;}
      proof=file;remove.hidden=false;
      let supported=false;try{supported=!!navigator.share&&!!navigator.canShare&&navigator.canShare({files:[proof]});}catch(_){}
      send.hidden=!supported;
      proofStatus.textContent=supported?'Comprovante selecionado: '+file.name+'. Toque em Enviar comprovante, escolha WhatsApp e o contato da loja.':'Comprovante selecionado: '+file.name+'. Este navegador não compartilha arquivos: abra o WhatsApp da loja e anexe esse arquivo manualmente.';
    });
    remove.addEventListener('click',()=>{proof=null;input.value='';send.hidden=true;remove.hidden=true;proofStatus.textContent='Comprovante removido.';});
    send.addEventListener('click',async()=>{if(!proof)return;send.disabled=true;try{await navigator.share({files:[proof]});proofStatus.textContent='Compartilhamento concluído. A loja ainda precisa conferir o pagamento no banco.';}catch(error){if(error.name!=='AbortError')proofStatus.textContent='Não foi possível compartilhar. Abra o WhatsApp da loja e anexe o comprovante manualmente.';}finally{send.disabled=false;}});
    proofBox.append(proofStatus,send,remove);section.append(proofBox);host.append(section);
  }
  window.NOWUP_PIX={attach};
  function init(){document.querySelectorAll('[data-pix-payment]').forEach(host=>{if(host.dataset.pixReady)return;host.dataset.pixReady='1';try{attach(host,JSON.parse(host.querySelector('script[type="application/json"]').textContent));}catch(_){}});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
