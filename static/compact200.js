/* V322: independent ordinary product and meal registration, without a wizard. */
(() => {
 'use strict';
 const make=(tag,text,attrs={})=>{const node=document.createElement(tag);if(text)node.textContent=text;Object.entries(attrs).forEach(([k,v])=>node.setAttribute(k,v));return node;};
 const section=title=>{const box=make('fieldset','',{class:'nu322-section full'});box.append(make('legend',title));return box;};
 function initializeCompact328(scope=document){scope.querySelectorAll('.pro-dashboard [data-editor192], [data-editor192]').forEach(host=>{
  if(!host.closest('.pro-dashboard'))return;
  const form=host.closest('form'),api=host._editor321;if(!form||!api||form.dataset.comboEditor301||form.dataset.compact200)return;
  form.dataset.compact200='322';form.dataset.extras317='true';form.dataset.simple200='false';
  const meal=form.dataset.mealEditor322==='1';form.dataset.meal317=String(meal);
  const submit=form.querySelector('button[type=submit],button:not([type])');if(!submit)return;submit.type='submit';
  api.heading.remove();
  if(!meal){
   // Remove food controls from ordinary registration. Keep existing values in the serializer when editing.
   for(const node of [api.ing.toggle.closest('label'),api.ing.body,api.shared,api.groups.toggle.closest('label'),api.groups.body,api.manualBox321,api.questionLabel333,api.utensils.closest('label'),api.notes.closest('label')])node?.remove();
   const modeLabel=api.mode?.closest('label'),picker=form.querySelector('[data-shared-picker155]'),paid=make('details','',{class:'full nu322-settings'});paid.append(make('summary','Adicionais pagos (opcional)'));if(modeLabel)paid.append(modeLabel);if(picker){const fold=make('details');fold.append(make('summary','Selecionar adicionais cadastrados'),picker);paid.append(fold);}paid.append(api.extras);host.before(paid);paid.open=api.mode?.value!=='none';
   const type=form.querySelector('[data-combo-type303]');function sync(){host.hidden=type?.value==='1';paid.hidden=type?.value==='1';}type?.addEventListener('change',sync);sync();
   return;
  }
  api.notes.checked=true;api.notes.closest('label').remove();api.ing.toggle.checked=true;api.ing.toggle.closest('label').remove();api.ing.sync();
  const ingredientBox=section('Ingredientes (opcional)'),importBox=make('details'),importTitle=make('summary','Galeria da minha loja — itens cadastrados');importBox.append(importTitle,api.ingredientSearch320,api.ingredientPicker320);importBox.append(api.ingredientLink320);if(api.ingredientStatus361)importBox.append(api.ingredientStatus361);importBox.addEventListener('toggle',()=>{if(importBox.open)api.refreshIngredients361?.();});
  const selectedIngredients325=make('details');selectedIngredients325.append(make('summary','Ingredientes selecionados'),api.list);
  // Selected ingredients stay visible; importing never replaces the manual list.
  api.ing.body.querySelector(':scope > p')?.remove();ingredientBox.append(make('p','Selecione os ingredientes já cadastrados na loja e marque os obrigatórios. Faltou algum? Toque em Importar ingrediente da galeria NowUp para salvar foto e preço sem sair da montagem. Os itens já selecionados serão mantidos e o novo ingrediente ficará salvo na loja.'),selectedIngredients325,api.addIngredient,importBox);api.ing.body.remove();api.addIngredient.textContent='+ Digitar ingrediente';
  function optionalRows(){selectedIngredients325.open=api.list.children.length>0;api.list.querySelectorAll('[aria-label=Ingrediente]').forEach(input=>input.required=false);}
  api.list.addEventListener('nowup:ingredients-added',optionalRows);api.addIngredient.addEventListener('click',optionalRows);api.ingredientPicker320.addEventListener('click',optionalRows);optionalRows();
  const paid=section('Adicionais pagos'),modeLabel=api.mode?.closest('label'),picker=form.querySelector('[data-shared-picker155]');if(modeLabel)paid.append(modeLabel);if(picker){const fold=make('details');fold.append(make('summary','Selecionar adicionais cadastrados'),picker);paid.append(fold);}paid.append(api.extras);
  const combo=section('Itens que vão neste combo'),comboOptions=make('div');api.comboLabel.lastChild.textContent=' Oferecer como combo';combo.append(api.comboLabel,comboOptions);
  const principal=make('p','');function name(){principal.textContent='Principal: '+(form.querySelector('[name=name]')?.value.trim()||'o próprio lanche ou refeição');}form.querySelector('[name=name]')?.addEventListener('input',name);name();combo.append(principal);combo.append(comboOptions);
  let config={};try{config=JSON.parse(host.dataset.editor192||'{}');}catch(_){}
  window.NOWUP_MEAL_GROUPS324(comboOptions,form,api,config);
  api.shared.remove();api.groups.toggle.closest('label').remove();api.groups.body.remove();
  api.utensils.checked=false;api.utensils.closest('label').remove();
  host.before(ingredientBox,paid,combo,api.manualBox321,api.questionLabel333);
  // Only the hidden configuration and its validation message remain in the original editor host.
 });}
 window.NOWUP_COMPACT328=initializeCompact328;initializeCompact328();
})();
