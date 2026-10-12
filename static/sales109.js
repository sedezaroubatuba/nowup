(() => {
  'use strict';
  const format=new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'});
  function tab(){const hash=location.hash||'#hoje';document.querySelectorAll('.sales109-tabs a').forEach(a=>a.classList.toggle('active',a.hash===hash));}
  tab();window.addEventListener('hashchange',tab);
  document.querySelectorAll('[data-s109-open]').forEach(b=>b.addEventListener('click',()=>document.getElementById(b.dataset.s109Open)?.showModal()));
  document.querySelectorAll('[data-s109-close]').forEach(b=>b.addEventListener('click',()=>b.closest('dialog').close()));
  const cents=raw=>{const text=raw.trim().replace(',','.');if(!text)return 0;if(!/^\d+(\.\d{1,2})?$/.test(text))return null;const [a,b='']=text.split('.');const result=Number(a)*100+Number(b.padEnd(2,'0'));return Number.isSafeInteger(result)?result:null;};
  document.querySelectorAll('[data-s109-payment]').forEach(form=>{
    function calculate(){
      let total=Number(form.dataset.paid),invalid=false,parts=[];
      form.querySelectorAll('[data-payment-method]').forEach(input=>{const value=cents(input.value);if(value===null){invalid=true;return;}if(value>0){total+=value;parts.push({method:input.dataset.paymentMethod,amount:(value/100).toFixed(2)});}});
      const remaining=Number(form.dataset.total)-total;
      form.querySelector('[data-payment-total]').textContent=format.format(total/100);
      form.querySelector('[data-payment-remaining]').textContent=format.format(remaining/100);
      form.querySelector('[data-payment-error]').textContent=invalid?'Confira os valores informados.':remaining<0?'Os pagamentos ultrapassam o total.':'';
      form.querySelector('[data-payment-submit]').disabled=invalid||remaining!==0||total<=0;
      form.elements.payments_json.value=JSON.stringify(parts);
      return !invalid&&remaining===0&&total>0;
    }
    form.addEventListener('input',calculate);form.addEventListener('submit',event=>{if(!calculate()){event.preventDefault();return;}form.querySelector('[data-payment-submit]').disabled=true;});calculate();
    form.addEventListener('keydown',event=>{
      if(event.key!=='Enter'||!event.target.matches('[data-payment-method]'))return;
      event.preventDefault();
      const inputs=[...form.querySelectorAll('[data-payment-method]')];
      const next=inputs[inputs.indexOf(event.target)+1];
      if(next){next.focus();next.select();return;}
      if(calculate()){form.querySelector('[data-payment-submit]').focus();return;}
      const message=form.querySelector('[data-payment-error]');
      if(!message.textContent)message.textContent='Confira o saldo: os pagamentos precisam quitar o total.';
      message.tabIndex=-1;message.focus();
    });
  });
  const params=new URLSearchParams(location.search);
  if(params.get('fechar')==='1'||params.get('adicionar')==='1'){const dialog=document.querySelector('section'+(location.hash==='#whatsapp'?'#whatsapp':'#comandas')+' dialog[id^="'+(params.get('fechar')==='1'?'pay-':'products-')+'"]');if(dialog){requestAnimationFrame(()=>dialog.showModal());params.delete('fechar');params.delete('adicionar');history.replaceState(null,'',location.pathname+'?'+params.toString()+location.hash);}}
})();

(() => {
  'use strict';
  const money=new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'});
  const normal=value=>String(value).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim();
  const el=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
  document.querySelectorAll('[data-live-add-product]').forEach(form=>{
    const search=form.querySelector('[data-product-search]'),select=form.elements.product_id;
    const options=[...select.options].map(o=>o.cloneNode(true));
    search.addEventListener('input',()=>{
      const query=normal(search.value),isCode=/^\d+$/.test(query);
      const matches=options.filter(o=>o.value&&(isCode?Number(o.value)===Number(query):normal(o.dataset.productName||o.textContent).includes(query)));
      select.replaceChildren(options[0].cloneNode(true),...matches.map(o=>o.cloneNode(true)));
      select.value=query&&matches.length===1?matches[0].value:'';
      form.querySelector('[data-product-feedback]').textContent=query&&!matches.length?'Nenhum produto disponível encontrado.':'';
    });
  });
  function update(section,data){
    const selected=section.querySelector('[data-current-sale]');
    selected.querySelectorAll('input[name="version"]').forEach(i=>i.value=String(data.version));
    document.querySelectorAll(`[data-sale-total="${data.id}"]`).forEach(n=>n.textContent=money.format(data.total_cents/100));
    document.querySelectorAll(`[data-sale-card="${data.id}"] [data-sale-items-count]`).forEach(n=>n.textContent=data.item_count+' item(ns)');
    const list=selected.querySelector('[data-live-sale-items]');list.replaceChildren();
    for(const item of data.items){
      const row=el('div'),copy=el('span');copy.append(el('b',`${item.quantity} × ${item.product_name}${item.product_id?' · Cód. '+item.product_id:''}`));
      if(item.notes)copy.append(el('small',item.notes));
      const form=el('form');form.method='post';form.action=`/painel/vendas-manuais/${data.id}/alterar`;
      for(const [name,value] of Object.entries({version:data.version,action:'remove_item',item_id:item.id})){
        const hidden=el('input');hidden.type='hidden';hidden.name=name;hidden.value=String(value);form.append(hidden);
      }
      const button=el('button','Retirar');button.className='s109-secondary';button.setAttribute('aria-label','Retirar '+item.product_name);form.append(button);
      row.append(copy,el('strong',money.format(item.quantity*item.unit_price_cents/100)),form);list.append(row);
    }
    if(!data.items.length)list.append(el('p','Adicione os produtos desta conta.'));
    selected.querySelectorAll('[data-s109-open^="pay-"]').forEach(b=>b.disabled=data.total_cents<=0);
    const payment=selected.querySelector('[data-s109-payment]');
    if(payment){payment.dataset.total=String(data.total_cents);payment.dataset.paid=String(data.paid);payment.dispatchEvent(new Event('input',{bubbles:true}));}
  }
  document.querySelectorAll('.sales109').forEach(section=>section.addEventListener('submit',async event=>{
    const form=event.target;
    if(!(form instanceof HTMLFormElement))return;
    const add=form.matches('[data-live-add-product]');
    const remove=!!form.closest('[data-live-sale-items]')&&form.elements.action?.value==='remove_item';
    if(!add&&!remove)return;
    event.preventDefault();
    const selected=section.querySelector('[data-current-sale]');
    if(selected.dataset.saving==='1')return;
    const feedback=section.querySelector('[data-product-feedback]');
    const submit=form.querySelector('button');
    const original=submit.textContent;
    selected.dataset.saving='1';submit.disabled=true;submit.textContent='Salvando…';
    if(feedback)feedback.textContent='';
    try{
      const response=await fetch(form.action,{method:'POST',credentials:'same-origin',headers:{Accept:'application/json'},body:new FormData(form)});
      let data;try{data=await response.json();}catch(_){throw new Error('Não foi possível confirmar o lançamento. Atualize a conta antes de repetir.');}
      if(!response.ok)throw new Error(data.detail||'Não foi possível salvar.');
      if(!Number.isInteger(data.version)||!Array.isArray(data.items))throw new Error('Atualize a conta para conferir o lançamento.');
      update(section,data);
      if(add){
        form.elements.quantity.value='1';form.elements.notes.value='';
        const search=form.querySelector('[data-product-search]');search.value='';search.dispatchEvent(new Event('input'));search.focus();
      }
      if(feedback)feedback.textContent=add?'Produto adicionado ✓':'Item retirado ✓';
    }catch(error){
      const message=error.message||'Falha de conexão. Atualize a conta antes de repetir.';
      if(feedback)feedback.textContent=message;
      if(remove)window.alert(message);
    }finally{selected.dataset.saving='0';submit.disabled=false;submit.textContent=original;}
  }));
})();
