/* V322: independent ordinary product and meal registration, without a wizard. */
(() => {
 'use strict';
 const make=(tag,text,attrs={})=>{const node=document.createElement(tag);if(text)node.textContent=text;Object.entries(attrs).forEach(([k,v])=>node.setAttribute(k,v));return node;};
 const section=title=>{const box=make('fieldset','',{class:'nu322-section full'});box.append(make('legend',title));return box;};
 document.querySelectorAll('.pro-dashboard [data-editor192]').forEach(host=>{
  const form=host.closest('form'),api=host._editor321;if(!form||!api||form.dataset.comboEditor301||form.dataset.compact200)return;
  form.dataset.compact200='322';form.dataset.extras317='true';form.dataset.simple200='false';
  const meal=form.dataset.mealEditor322==='1';form.dataset.meal317=String(meal);
  const submit=form.querySelector('button[type=submit],button:not([type])');if(!submit)return;submit.type='submit';
  api.heading.remove();
  if(!meal){
   // Remove food controls from ordinary registration. Keep existing values in the serializer when editing.
   for(const node of [api.ing.toggle.closest('label'),api.ing.body,api.shared,api.groups.toggle.closest('label'),api.groups.body,api.manualBox321,api.utensils.closest('label'),api.notes.closest('label')])node?.remove();
   const modeLabel=api.mode?.closest('label'),picker=form.querySelector('[data-shared-picker155]'),paid=make('details','',{class:'full nu322-settings'});paid.append(make('summary','Adicionais pagos (opcional)'));if(modeLabel)paid.append(modeLabel);if(picker)paid.append(picker);paid.append(api.extras);host.before(paid);paid.open=api.mode?.value!=='none';
   const type=form.querySelector('[data-combo-type303]');function sync(){host.hidden=type?.value==='1';paid.hidden=type?.value==='1';}type?.addEventListener('change',sync);sync();
   return;
  }
  api.notes.checked=true;api.notes.closest('label').remove();api.ing.toggle.checked=true;api.ing.toggle.closest('label').remove();api.ing.sync();
  const ingredientBox=section('Ingredientes (opcional)'),importBox=make('details'),importTitle=make('summary','Importar ingredientes cadastrados');importBox.append(importTitle,api.ingredientSearch320,api.ingredientPicker320,api.ingredientLink320);
  // Selected ingredients stay visible; importing never replaces the manual list.
  api.ing.body.querySelector(':scope > p')?.remove();ingredientBox.append(make('p','Digite os ingredientes ou importe do cadastro. Marque como obrigatório o que o cliente não poderá retirar.'),api.list,api.addIngredient,importBox);api.ing.body.remove();api.addIngredient.textContent='+ Digitar ingrediente';
  function optionalRows(){api.list.querySelectorAll('[aria-label=Ingrediente]').forEach(input=>input.required=false);}
  api.addIngredient.addEventListener('click',optionalRows);api.ingredientPicker320.addEventListener('click',optionalRows);optionalRows();
  const paid=section('Adicionais pagos'),modeLabel=api.mode?.closest('label'),picker=form.querySelector('[data-shared-picker155]');if(modeLabel)paid.append(modeLabel);if(picker)paid.append(picker);paid.append(api.extras);
  const combo=section('Combo'),comboOptions=make('div');api.comboLabel.lastChild.textContent=' Oferecer este lanche ou refeição como combo';combo.append(api.comboLabel,comboOptions);
  const principal=make('p','');function name(){principal.textContent='Principal: '+(form.querySelector('[name=name]')?.value.trim()||'o próprio lanche ou refeição');}form.querySelector('[name=name]')?.addEventListener('input',name);name();comboOptions.append(principal,make('small','Escolha bebidas, batata ou outros acompanhamentos já incluídos no preço do combo.'));
  const sides=make('details'),sideTitle=make('summary','Batata e acompanhamentos');sides.append(sideTitle,api.sidePicker,api.sideCountLabel,api.requiredLabel);
  const drinks=make('details'),drinkTitle=make('summary','Bebidas');drinks.append(drinkTitle,api.drinkBody);comboOptions.append(drinks,sides);
  sides.open=!!sides.querySelector('input:checked');drinks.open=!!drinks.querySelector('input:checked');if(sides.open||drinks.open)api.isCombo.checked=true;
  function syncCombo(){comboOptions.hidden=!api.isCombo.checked;api.drinkBody.hidden=false;comboOptions.querySelectorAll('input[type=number]').forEach(input=>input.disabled=!api.isCombo.checked);}
  api.isCombo.addEventListener('change',syncCombo);syncCombo();api.shared.remove();
  const other=make('details','',{class:'full nu322-settings'});other.append(make('summary','Outras opções (opcional)'),api.groups.toggle.closest('label'),api.groups.body,api.utensils.closest('label'));
  other.open=api.groups.toggle.checked||api.utensils.checked;
  host.before(ingredientBox,paid,combo,api.manualBox321,other);
  // Only the hidden configuration and its validation message remain in the original editor host.
 });
})();
