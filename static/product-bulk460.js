/* V460: searchable, twenty-product, cross-search selector. Server remains authoritative. */
(()=>{'use strict';
 const root=document.querySelector(".nu460-batch");
 const catalogNode=document.getElementById("nu455-product-names");
 if(!root||!catalogNode)return;
 let catalog=[];try{catalog=JSON.parse(catalogNode.textContent||"[]");}catch(_){}
 catalog=catalog.filter(item=>Number.isInteger(Number(item.id))&&Number(item.id)>0);
 const byId=new Map(catalog.map(item=>[String(item.id),item]));
 const selected=new Set();
 const limit=20;
 const form=root.querySelector("[data-bulk-form460]");
 const filter=root.querySelector("[data-bulk-filter465]");
 const search=root.querySelector("[data-bulk-search460]");
 const results=root.querySelector("[data-bulk-results460]");
 const count=root.querySelector("[data-bulk-count460]");
 const selectedBox=root.querySelector("[data-bulk-selected460]");
 const idsHost=root.querySelector("[data-bulk-ids460]");
 const operation=root.querySelector("[data-bulk-operation460]");
 const category=root.querySelector("[data-bulk-category460]");
 const subcategory=root.querySelector("[data-bulk-subcategory460]");
 const targetSearch=root.querySelector("[data-bulk-target-search460]");
 const target=root.querySelector("[data-bulk-target460]");
 const priceBox=root.querySelector("[data-bulk-price-fields460]");
 const pricesJson=root.querySelector("[data-bulk-prices-json460]");
 const status=root.querySelector("[data-bulk-status460]");
 const button=root.querySelector("[data-bulk-submit460]");
 const normalize=v=>String(v||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase().trim();
 const money=n=>(Number(n||0)/100).toLocaleString("pt-BR",{style:"currency",currency:"BRL"});
 let priceDrafts=new Map();
 const msg=s=>{status.textContent=s||"";};
 const make=(tag,text,cls)=>{const el=document.createElement(tag);if(cls)el.className=cls;if(text!==undefined&&text!==null)el.textContent=text;return el;};
 const subcategoryOptions=new Map([...subcategory.options].map(option=>[option.value,option]));
 function currentSubcategory(item){
  const option=subcategoryOptions.get(String(item.subcategory));
  return option?.dataset.parent&&normalize(option.dataset.parent)===normalize(item.category)?option.textContent.trim():"";
 }
 const categories=new Map();
 for(const item of catalog){
  if(item.category&&!categories.has(normalize(item.category)))categories.set(normalize(item.category),item.category);
 }
 for(const [key,name] of [...categories].sort((a,b)=>a[1].localeCompare(b[1],"pt-BR"))){
  const option=make("option",name);option.value=key;filter.append(option);
 }
 let visibleLimit=40;
 function priceInput(){
  priceBox.querySelectorAll("input[data-price460]").forEach(input=>{priceDrafts.set(input.dataset.price460,input.value);});
  priceBox.replaceChildren();
  for(const id of selected){
   const item=byId.get(id),label=make("label",null,"nu460-price-row");
   const name=make("span",item.name);
   const small=make("small","Atual: "+money(item.price));
   const field=make("input");field.dataset.price460=id;field.inputMode="decimal";field.required=operation.value==="prices";
   field.setAttribute("aria-label","Novo preço de "+item.name);
   field.placeholder="Novo preço (R$)";
   field.value=priceDrafts.has(id)?priceDrafts.get(id):(Number(item.price||0)/100).toFixed(2).replace(".",",");
   label.append(name,small,field);priceBox.append(label);
  }
 }
 function renderResults(){
  const scroll=results.scrollTop;
  results.replaceChildren();
  const q=normalize(search.value);
  const matches=catalog.filter(item=>(!filter.value||normalize(item.category)===filter.value)&&
   (!q||normalize(item.name+" "+item.id+" "+item.category+" "+currentSubcategory(item)).includes(q)));
  if(!matches.length){results.append(make("p","Nenhum produto encontrado.","nu460-info"));return;}
  for(const item of matches.slice(0,visibleLimit)){
   const id=String(item.id),row=make("label",null,"nu460-result");
   const checkbox=make("input");
   checkbox.type="checkbox";checkbox.value=id;checkbox.checked=selected.has(id);
   checkbox.disabled=!checkbox.checked&&selected.size>=limit;
   checkbox.setAttribute("aria-label","Selecionar "+item.name);
   checkbox.addEventListener("change",()=>{
    if(checkbox.checked){
     if(selected.size>=limit){checkbox.checked=false;msg("O limite é de "+limit+" produtos por lote. Salve este lote antes de escolher outros.");return;}
     selected.add(id);
    }else selected.delete(id);
    redraw();
    results.querySelector('input[value="'+id+'"]')?.focus({preventScroll:true});
   });
   const data=make("span",null,"nu460-result-text");
   data.append(make("strong",item.name),make("small",(item.category||"Sem categoria")+" · "+money(item.price)+" · Cód. "+id));
   const sub=currentSubcategory(item);
   const badge=make("span",sub?"✓ "+sub:"Sem subcategoria","nu465-subcategory");
   if(sub)badge.classList.add("nu465-assigned");
   data.append(badge);
   row.append(checkbox,data);results.append(row);
  }
  if(matches.length>visibleLimit){
   const more=make("button","Ver mais produtos","nu465-more");
   more.type="button";more.addEventListener("click",()=>{
    const next=visibleLimit;visibleLimit+=40;renderResults();
    results.querySelectorAll("input")[next]?.focus();
   });results.append(more);
  }
  results.scrollTop=scroll;
 }
 function renderSelected(){
  count.textContent=selected.size+" de "+limit+" produtos selecionados";
  selectedBox.replaceChildren();idsHost.replaceChildren();
  if(!selected.size){selectedBox.append(make("span","Marque os produtos na lista de busca acima.","nu460-info"));}
  for(const id of selected){
   const item=byId.get(id),chip=make("span",null,"nu460-chip");
   chip.append(make("span",item.name));
   const remove=make("button","×");remove.type="button";remove.setAttribute("aria-label","Retirar "+item.name);
   remove.addEventListener("click",()=>{selected.delete(id);redraw();});
   chip.append(remove);selectedBox.append(chip);
   const hidden=make("input");hidden.type="hidden";hidden.name="selected_ids";hidden.value=id;idsHost.append(hidden);
  }
  button.textContent=selected.size?"Conferir alterações ("+selected.size+")":"Conferir alterações";
  button.disabled=!selected.size;
 }
 function renderMode(){
  root.querySelectorAll("[data-bulk-mode460]").forEach(section=>{
   const active=section.dataset.bulkMode460===operation.value;
   section.hidden=!active;
   section.querySelectorAll("input,select,textarea").forEach(input=>{
    if(input.name==="prices_json"||input.name==="target_id"||input.name==="new_category"||
       input.name==="subcategory_id261"||input.name==="available_value"||input.dataset.price460){
     input.disabled=!active;
    }
   });
  });
  if(operation.value==="prices")priceInput();
  else priceBox.querySelectorAll("input[data-price460]").forEach(input=>{input.required=false;input.disabled=true;});
 }
 function syncSubcats(){
  const current=String(subcategory.value);
  let valid=false;
  [...subcategory.options].forEach(option=>{
   if(option.value==="0")return;
   const match=normalize(option.dataset.parent)===normalize(category.value);
   option.disabled=!match;option.hidden=!match;
   if(option.value===current&&match)valid=true;
  });
  if(!valid)subcategory.value="0";
 }
 function renderTargets(){
  const old=target.value;
  target.replaceChildren();
  const placeholder=make("option","Selecione o produto sugerido");placeholder.value="0";target.append(placeholder);
  const q=normalize(targetSearch.value);
  let list=catalog.filter(item=>!selected.has(String(item.id))&&(!q||normalize(item.name+" "+item.id).includes(q))).slice(0,35);
  const remembered=byId.get(old);
  if(remembered&&!selected.has(String(remembered.id))&&!list.some(item=>String(item.id)===old))list=[remembered,...list];
  list.forEach(item=>{const opt=make("option",item.name+" · "+money(item.price));opt.value=item.id;target.append(opt);});
  if([...target.options].some(opt=>opt.value===old))target.value=old;
 }
 function redraw(){renderResults();renderSelected();renderMode();renderTargets();}
 function updateSource(){
  visibleLimit=40;results.scrollTop=0;
  search.placeholder=filter.value?"Buscar em "+categories.get(filter.value):"Buscar por nome ou código";
  renderResults();
 }
 search.addEventListener("input",updateSource);
 filter.addEventListener("change",updateSource);
 operation.addEventListener("change",()=>{renderMode();msg("");});
 category.addEventListener("change",syncSubcats);
 targetSearch.addEventListener("input",renderTargets);
 root.querySelector("[data-bulk-clear460]").addEventListener("click",()=>{selected.clear();priceDrafts.clear();msg("");redraw();});
 form.addEventListener("submit",async event=>{
  if(form.dataset.confirmed460==="true"){form.dataset.confirmed460="";return;}
  event.preventDefault();
  if(!selected.size){msg("Marque ao menos um produto.");search.focus();return;}
  if(selected.size>limit){msg("Limite de "+limit+" produtos por operação.");return;}
  const mode=operation.value;
  let detail="",warning="",names=[...selected].map(id=>byId.get(id)?.name||("Produto "+id));
  if(mode==="related"){
   if(!target.value||target.value==="0"){msg("Escolha o produto sugerido no Leve Junto.");target.focus();return;}
   if(selected.has(target.value)){msg("O produto sugerido não pode estar entre os produtos de origem.");return;}
   detail="Adicionar "+(byId.get(target.value)?.name||"o produto")+" ao Leve Junto de "+selected.size+" produto(s).";
  }else if(mode==="category"){
   if(!category.value){msg("Escolha a nova categoria.");category.focus();return;}
   const linked=[...selected].filter(id=>Number(byId.get(id)?.parent||0)>0);
   if(linked.length){msg("Itens vinculados a agrupadores não podem mudar individualmente de categoria. Retire-os da seleção ou edite a capa.");return;}
   const newSubcategory=subcategory.value==="0"?"":subcategory.selectedOptions[0]?.textContent.trim();
   const destination=category.value+" / "+(newSubcategory||"Sem subcategoria");
   let replacements=0;
   names=[...selected].map(id=>{
    const item=byId.get(id),current=currentSubcategory(item);
    if(current&&(String(item.subcategory)!==subcategory.value||normalize(item.category)!==normalize(category.value)))replacements++;
    return item.name+"\n"+(item.category||"Sem categoria")+" / "+(current||"Sem subcategoria")+" → "+destination;
   });
   if(replacements)warning=replacements===1?"1 produto terá a subcategoria atual alterada. Confira a troca antes de salvar.":replacements+" produtos terão a subcategoria atual alterada. Confira as trocas antes de salvar.";
   detail="Categoria e subcategoria após salvar";
  }else if(mode==="prices"){
   const values={};let changed=false;
   priceBox.querySelectorAll("input[data-price460]").forEach(input=>{
    values[input.dataset.price460]=input.value.trim();
    if(!input.value.trim())input.setCustomValidity("Informe o preço.");
    else input.setCustomValidity("");
    const parsed=Number(input.value.trim().replace(/\./g,"").replace(",","."));
    if(!Number.isFinite(parsed)||parsed<=0)input.setCustomValidity("Preço válido deve ser maior que zero.");
    const product=byId.get(input.dataset.price460);
    const entered=Number(input.value.trim().replace(/\./g,"").replace(",","."));
    if(product&&Number.isFinite(entered)&&Math.round(entered*100)!==Number(product.price))changed=true;
   });
   if(!form.reportValidity()){msg("Confira os preços. Todos devem ser positivos.");return;}
   pricesJson.value=JSON.stringify(values);
   if(!changed){msg("Você não alterou nenhum preço deste lote.");return;}
   detail="Atualizar os preços individuais dos "+selected.size+" produtos selecionados.";
  }else{
   const field=form.querySelector('[name=available_value]');
   if(!field?.value){msg("Escolha Disponível ou Indisponível.");field?.focus();return;}
   detail=(field.value==="1"?"Ativar ":"Desativar ")+selected.size+" produto(s).";
  }
  msg("");
  const preview=names.map((n,i)=>(i+1)+". "+n).join(mode==="category"?"\n\n":"\n");
  const message=detail+"\n\n"+preview+"\n\nConfirmar? Se algum produto tiver erro, nenhum será alterado.";
  const confirmed=window.NowUpDialog?.confirm?await window.NowUpDialog.confirm(message,{title:"Conferir alterações",confirm:"Confirmar e salvar",cancelLabel:"Voltar",warning}):window.confirm([message,warning].filter(Boolean).join("\n\n"));
  if(confirmed){form.dataset.confirmed460="true";form.requestSubmit(button);}
 });
 syncSubcats();redraw();
})();