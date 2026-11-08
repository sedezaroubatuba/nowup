/* Receipt images come only from the server-validated checkout snapshot. */
(()=>{'use strict';
  const W=1000,H=2400,M=48,PURPLE='#7136bf',PALE='#f1e9fc',INK='#241a31';
  function loadImage(src){return new Promise(resolve=>{const img=new Image();let done=false;const finish=value=>{if(done)return;done=true;clearTimeout(timer);resolve(value);};const timer=setTimeout(()=>finish(null),5000);img.onload=()=>finish(img);img.onerror=()=>finish(null);img.src=src;});}
  function lines(ctx,text,width){
    const result=[];
    for(const paragraph of String(text||'').split('\n')){
      let line='';
      for(const word of paragraph.split(/\s+/)){
        if(!word)continue;
        if(ctx.measureText(line+(line?' ':'')+word).width<=width){line+=(line?' ':'')+word;continue;}
        if(line){result.push(line);line='';}
        let rest=word;
        while(ctx.measureText(rest).width>width){let n=1;while(n<rest.length&&ctx.measureText(rest.slice(0,n+1)).width<=width)n++;result.push(rest.slice(0,n));rest=rest.slice(n);}
        line=rest;
      }
      result.push(line);
    }
    return result;
  }
  async function render(data){
    const logoURL=new URL(data.logo||'/',location.origin);
    const [logo,brand,pixQR]=await Promise.all([logoURL.origin===location.origin?loadImage(logoURL.href):null,loadImage('/static/nowup-logo185.png?v=196'),/^data:image\/png;base64,/.test(data.pix?.qr_image||'')?loadImage(data.pix.qr_image):null]);
    const pages=[];let canvas,ctx,y;
    function font(size,bold=false){ctx.font=(bold?'700 ':'400 ')+size+'px Arial, sans-serif';}
    function text(value,x,width,size=30,bold=false,color=INK){font(size,bold);ctx.fillStyle=color;for(const row of lines(ctx,value,width)){ctx.fillText(row,x,y);y+=Math.ceil(size*1.32);}}
    function rect(x,top,width,height,color,radius=18){ctx.fillStyle=color;ctx.beginPath();ctx.roundRect(x,top,width,height,radius);ctx.fill();}
    function start(){
      canvas=document.createElement('canvas');canvas.width=W;canvas.height=H;ctx=canvas.getContext('2d');ctx.textBaseline='top';ctx.fillStyle='#fff';ctx.fillRect(0,0,W,H);
      rect(0,0,W,190,PURPLE,0);rect(M,36,112,112,'#fff',56);
      if(logo){ctx.save();ctx.beginPath();ctx.arc(M+56,92,52,0,Math.PI*2);ctx.clip();ctx.drawImage(logo,M+4,40,104,104);ctx.restore();}
      else{font(50,true);ctx.fillStyle=PURPLE;ctx.fillText(String(data.store_name||'Loja').slice(0,1).toUpperCase(),M+38,66);}
      y=42;text(data.store_name,M+140,W-2*M-140,34,true,'#fff');
      y=214;text('Resumo do pedido',M,W-2*M,44,true,PURPLE);
      if(data.order_code)text('Pedido '+data.order_code,M,W-2*M,27,true);
      text(data.status||'Aguardando confirmação da loja',M,W-2*M,28,false,PURPLE);y+=22;
    }
    function finish(last=false){
      y+=22;ctx.strokeStyle='#dfd0ed';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(M,y);ctx.lineTo(W-M,y);ctx.stroke();y+=20;
      if(brand){const ratio=brand.width/brand.height;ctx.drawImage(brand,M,y,160,160/ratio);}
      font(24);ctx.fillStyle='#695c74';ctx.fillText('Tecnologia NowUp',M+185,y+8);y+=70;
      font(21);ctx.fillText('Resumo do pedido • página '+(pages.length+1)+(last?' • fim':''),M,y);y+=42;
      const cropped=document.createElement('canvas');cropped.width=W;cropped.height=y;cropped.getContext('2d').drawImage(canvas,0,0,W,y,0,0,W,y);pages.push(cropped);
    }
    function reserve(height){if(y+height>H-185){finish();start();}}
    function block(title,body){
      font(28,true);let heading=lines(ctx,title,W-2*M-40);
      font(29);const rows=body.flatMap(line=>lines(ctx,'• '+line,W-2*M-40));
      let offset=0,first=true;
      do{
        const titleRows=first?heading:[...heading,'(continuação)'];
        reserve(titleRows.length*37+100);
        const available=Math.max(1,Math.floor((H-185-y-titleRows.length*37-48)/39));
        const part=rows.slice(offset,offset+available),height=titleRows.length*37+part.length*39+42;
        rect(M,y,W-2*M,height,PALE);y+=18;
        font(28,true);ctx.fillStyle=PURPLE;for(const row of titleRows){ctx.fillText(row,M+20,y);y+=37;}
        font(29);ctx.fillStyle=INK;for(const row of part){ctx.fillText(row,M+20,y);y+=39;}
        y+=24;offset+=part.length;first=false;
      }while(offset<rows.length);
      y+=18;
    }
    start();
    for(const entry of data.blocks||[])block(entry.title,entry.lines||[]);
    if(pixQR){
      reserve(680);text('Pagar com Pix',M,W-2*M,32,true,PURPLE);
      text('Valor: '+data.pix.amount,M,W-2*M,27);
      text('Recebedor: '+data.pix.receiver,M,W-2*M,27);
      ctx.drawImage(pixQR,(W-360)/2,y,360,360);y+=374;
      text('Confira o favorecido no banco.',M,W-2*M,25);
      text('Confirmação do pagamento feita pela loja.',M,W-2*M,25);y+=16;
    }
    reserve(110);rect(M,y,W-2*M,90,PURPLE);font(40,true);ctx.fillStyle='#fff';ctx.fillText('TOTAL',M+22,y+24);ctx.textAlign='right';ctx.fillText(data.total,W-M-22,y+24);ctx.textAlign='left';y+=100;finish(true);
    const files=[];
    for(let index=0;index<pages.length;index++){
      const blob=await new Promise(resolve=>pages[index].toBlob(resolve,'image/png'));
      if(!blob)throw new Error('Não foi possível gerar a notinha.');
      files.push(new File([blob],'pedido-'+(data.order_code||'nowup')+'-'+(index+1)+'.png',{type:'image/png'}));
    }
    return files;
  }
  async function attach(host,data){
    if(!data||data.version!==1||!Array.isArray(data.blocks))return;
    const group=document.createElement('section');group.setAttribute('aria-label','Notinha do pedido');
    const title=document.createElement('h3');title.textContent='Notinha do pedido';group.append(title);
    const hint=document.createElement('p');hint.textContent='Gerando a notinha…';hint.setAttribute('role','status');group.append(hint);host.append(group);
    const urls=[];let disposed=false;host.receiptCleanup=()=>{disposed=true;urls.forEach(URL.revokeObjectURL);};
    try{
      const files=await render(data);if(disposed||!host.isConnected)return;
      title.textContent='Sua notinha está pronta';hint.textContent='Toque em Enviar notinha pelo WhatsApp, escolha WhatsApp, selecione o contato da loja e confirme o envio. A notinha será enviada como imagem.';
      const preview=document.createElement('details');const summary=document.createElement('summary');summary.textContent='Ver notinha ('+files.length+(files.length===1?' imagem)':' imagens)');preview.append(summary);
      files.forEach((file,index)=>{const url=URL.createObjectURL(file);urls.push(url);const img=document.createElement('img');img.src=url;img.alt='Notinha do pedido, página '+(index+1);img.style.cssText='display:block;width:100%;max-width:600px;height:auto;margin:12px auto;border:1px solid #e5daee;border-radius:12px';preview.append(img);const download=document.createElement('a');download.href=url;download.download=file.name;download.className='btn soft full-btn';download.textContent=files.length===1?'Baixar notinha':'Baixar página '+(index+1);preview.append(download);});
      preview.open=true;group.append(preview);
      let supported=false;try{supported=!!navigator.share&&!!navigator.canShare&&navigator.canShare({files});}catch(_){}
      if(supported){const button=document.createElement('button');button.type='button';button.className='btn primary full-btn';button.textContent='Enviar notinha pelo WhatsApp';button.addEventListener('click',()=>{button.disabled=true;navigator.share({files}).then(()=>{hint.textContent='Compartilhamento concluído. Aguarde a confirmação da loja.';}).catch(error=>{if(error.name!=='AbortError')hint.textContent='Não foi possível compartilhar. Abra a prévia, baixe a notinha e anexe no WhatsApp.';}).finally(()=>{button.disabled=false;});});group.insertBefore(button,preview);}
      else hint.textContent='Abra a prévia, baixe a notinha e anexe no WhatsApp da loja. É o mesmo pedido da mensagem de texto.';
    }catch(_){hint.textContent='A notinha não pôde ser gerada neste aparelho. Você pode enviar o pedido em texto pelo botão do WhatsApp.';}
  }
  window.NOWUP_RECEIPT={attach,render};
})();
