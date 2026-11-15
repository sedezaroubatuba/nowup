/* Create a paid extra without submitting or resetting the surrounding product. */
(()=>{'use strict';
 const node=(tag,text,attrs={})=>{const e=document.createElement(tag);if(text)e.textContent=text;Object.entries(attrs).forEach(([k,v])=>e.setAttribute(k,v));return e;};
 let count=0;
 for(const picker of document.querySelectorAll('[data-shared-picker155]')){
  const product=picker.closest('form'),mode=product?.querySelector('[name=extras_mode]');if(!product||!mode)continue;
  const box=node('details','',{class:'full nu442-inline'}),title=node('summary','＋ Cadastrar adicional aqui'),body=node('div','',{class:'nu442-fields'}),feedback=node('p','',{role:'status','aria-live':'polite'});
  // External form ownership avoids nested forms and product validation interference.
  const owner=node('form','',{id:'nu442-extra-'+(++count),hidden:''});document.body.append(owner);
  const field=(label,type)=>{const wrap=node('label',label),input=node('input','',{class:'input',type,form:owner.id});wrap.append(input);body.append(wrap);return input;};
  const name=field('Nome do adicional','text');name.required=true;name.maxLength=100;
  const price=field('Preço do adicional (obrigatório)','text');price.required=true;price.inputMode='decimal';price.placeholder='Ex.: 5,00';
  const photo=field('Foto (opcional)','file');photo.accept='image/*';
  const save=node('button','Salvar e selecionar adicional',{type:'button',class:'btn primary'});body.append(save,feedback);box.append(title,body);mode.closest('label').after(box);
  let busy=false;
  save.addEventListener('click',async()=>{
   if(busy||!name.reportValidity()||!price.reportValidity())return;
   const raw=price.value.trim().replace(/^R\$\s*/,'');let normalized=raw.includes(',')?raw.replace(/\./g,'').replace(',','.'):raw;
   if(!/^\d+(?:\.\d{1,2})?$/.test(normalized)||Number(normalized)<=0){feedback.textContent='Informe um preço maior que zero, com até duas casas decimais.';return;}
   busy=true;save.disabled=true;feedback.textContent='Salvando adicional…';
   try{
    const data=new FormData();data.set('name',name.value.trim());data.set('price',normalized);data.set('inline_paid442','1');if(photo.files[0])data.set('photo',photo.files[0]);
    const r=await fetch('/painel/cardapio/ingredientes320',{method:'POST',body:data,credentials:'same-origin',headers:{Accept:'application/json'}});
    if(!r.headers.get('content-type')?.includes('application/json'))throw Error('Sua sessão precisa ser renovada. Os dados deste produto continuam na tela.');
    const extra=await r.json();if(!r.ok)throw Error(typeof extra.detail==='string'?extra.detail:'Não foi possível salvar o adicional.');
    for(const target of document.querySelectorAll('[data-shared-picker155]')){
     let check=[...target.querySelectorAll('input[name=extra_ids]')].find(x=>x.value===String(extra.id));
     if(!check){const label=node('label','',{class:'check'});check=node('input','',{type:'checkbox',name:'extra_ids',value:String(extra.id)});label.append(check,document.createTextNode(' '+extra.name+' · + '+(extra.price_cents/100).toLocaleString('pt-BR',{style:'currency',currency:'BRL'})));target.querySelectorAll('p').forEach(x=>x.remove());target.append(label);}
     if(target===picker)check.checked=true;
    }
    if(!['all','selected'].includes(mode.value))mode.value='selected';mode.dispatchEvent(new Event('change',{bubbles:true}));
    const fold=picker.closest('details');if(fold)fold.open=true;
    name.value=price.value=photo.value='';feedback.textContent='Adicional salvo na loja e selecionado neste produto. Continue o cadastro e salve o produto.';
   }catch(e){feedback.textContent=e.message;}finally{busy=false;save.disabled=false;}
  });
 }
 const style=node('style');style.textContent='.nu442-inline{border:1px solid #dac5ed;border-radius:12px;padding:12px;margin:10px 0;background:#faf7fd}.nu442-inline summary{color:#602795;font-weight:700;cursor:pointer}.nu442-fields{display:grid;gap:10px;padding-top:12px;min-width:0}.nu442-fields label{display:grid;gap:5px}.nu442-fields input{max-width:100%;box-sizing:border-box}.nu442-fields [role=status]{font-size:14px;overflow-wrap:anywhere}';document.head.append(style);
})();
