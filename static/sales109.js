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
  });
  const params=new URLSearchParams(location.search);
  if(params.get('fechar')==='1'||params.get('adicionar')==='1'){const dialog=document.querySelector('section'+(location.hash==='#whatsapp'?'#whatsapp':'#comandas')+' dialog[id^="'+(params.get('fechar')==='1'?'pay-':'products-')+'"]');if(dialog){requestAnimationFrame(()=>dialog.showModal());params.delete('fechar');params.delete('adicionar');history.replaceState(null,'',location.pathname+'?'+params.toString()+location.hash);}}
})();
