/* Separate-purchase comparison; never changes the amount charged for a combo. */
(() => {
 'use strict';
 const money=n=>(n/100).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
 function parsePrice(raw){const s=String(raw||'').replace(/R\$|\s/g,'');const n=Number(s.includes(',')?s.replace(/\./g,'').replace(',','.'):s);return Number.isFinite(n)&&n>=0?Math.round(n*100):null;}
 function compare(config,prices,final,chosen={}){
  if(!config?.combo_items?.length||!Number.isSafeInteger(final)||final<0)return null;
  let total=0,variable=false;
  for(const item of config.combo_items){
   const qty=item.quantity;if(!Number.isInteger(qty)||qty<1||qty>99)return null;
   const group=(config.groups||[]).find(g=>g.id===item.group_id301);
   if(group){
    if(!group.product_ids?.length||group.product_ids.length!==group.options.length)return null;
    const list=group.product_ids.map(id=>prices[String(id)]);if(list.some(p=>!Number.isSafeInteger(p)||p<0))return null;
    const values=chosen[group.id];
    if(Array.isArray(values)&&values.length===qty){for(const name of values){const ix=group.options.indexOf(name);if(ix<0)return null;total+=list[ix];}}
    else{total+=Math.min(...list)*qty;variable=variable||Math.min(...list)!==Math.max(...list);}
   }else{const p=prices[String(item.product_id)];if(!Number.isSafeInteger(p)||p<0)return null;total+=p*qty;}
  }
  return {separate:total,final,saving:Math.max(0,total-final),variable};
 }
 function render(node,config,prices,final,chosen={}){
  node.replaceChildren();const value=compare(config,prices,final,chosen);node.hidden=!value;if(!value)return null;
  const line=document.createElement('p');line.textContent=(value.variable?'Comprando separado, a partir de: ':'Comprando separado: ')+money(value.separate);line.className='nu303-separate';node.append(line);
  const price=document.createElement('strong');price.textContent='Preço do combo: '+money(final);node.append(price);
  if(value.saving>0){const badge=document.createElement('p');badge.className='nu303-saving';badge.textContent=(value.variable?'Economize a partir de ':'Economize ')+money(value.saving);node.append(badge);}
  return value;
 }
 window.NOWUP_COMBO_PRICE303={compare,render,money,parsePrice};
})();
