/* V456: cost fields are always optional, whether or not a legacy switch was enabled. */
(()=>{'use strict';
 const root=document.querySelector('.pro-dashboard');
 if(!root)return;
 let config={costs:{}};
 const parse=value=>{
  const raw=String(value||'').trim().replace(/\s/g,'');
  if(!raw)return NaN;
  const normalized=raw.includes(',')?raw.replace(/\./g,'').replace(',','.'):raw;
  return Number(normalized);
 };
 function apply(){
  root.querySelectorAll('form.product-form').forEach(form=>{
   if(!/^\/painel\/cardapio\/produtos(?:\/\d+)?$/.test(new URL(form.action,location.href).pathname))return;
   const id=new URL(form.action,location.href).pathname.match(/produtos\/(\d+)$/)?.[1];
   const label= form.querySelector('[data-cost-label456]')||document.createElement('label');
   if(!label.isConnected){
    label.dataset.costLabel456='1';
    label.className='nu456-cost';
    label.append(document.createTextNode(form.querySelector('[name=sold_by_weight370]')?.value==='1'?'Preço de custo por kg (opcional)':'Preço de custo (opcional)'));
    const input=document.createElement('input');
    input.name='cost_price413';input.inputMode='decimal';input.required=false;
    input.placeholder='Se vazio, usar margem ilustrativa de 20%';
    if(id && config.costs?.[id]!==undefined)input.value=(config.costs[id]/100).toFixed(2).replace('.',',');
    label.append(input);
    const info=document.createElement('small');info.className='nu456-margin-info';
    label.append(info);
    (form.querySelector('.nu410-basic')||form).append(label);
   }
   const cost=label.querySelector('[name=cost_price413]');
   if(!cost)return;
   if(id&&config.costs?.[id]!==undefined&&cost.dataset.loaded456!=='1'){
    cost.value=(config.costs[id]/100).toFixed(2).replace('.',',');
   }
   cost.dataset.loaded456='1';
   if(!form.dataset.margin456){
    form.dataset.margin456='1';
    const update=()=>{
     const price=parse(form.querySelector('[name=price]')?.value),actual=parse(cost.value),node=label.querySelector('.nu456-margin-info');
     if(!Number.isFinite(price)||price<=0){node.textContent='Informe o preço de venda para calcular a margem.';return;}
     if(!Number.isFinite(actual)){node.textContent='Margem bruta ilustrativa: 20% (custo não informado).';return;}
     const margin=(price-actual)/price*100;
     node.textContent='Margem bruta calculada com custo informado: '+margin.toLocaleString('pt-BR',{maximumFractionDigits:2})+'%.';
    };
    form.addEventListener('input',update);
    update();
   }
  });
 }
 async function load(){
  try{const response=await fetch('/painel/custos/config',{credentials:'same-origin',cache:'no-store'});
   if(response.ok)config=await response.json();
  }catch(_){}
  apply();
 }
 let pending=false;
 new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;apply();});})
  .observe(root,{childList:true,subtree:true});
 apply();load();
})();