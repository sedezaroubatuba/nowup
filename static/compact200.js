/* Compact product editor: advanced fields are optional and existing values survive until saved. */
(() => {
 'use strict';
 document.querySelectorAll('.pro-dashboard [data-editor192]').forEach((host,index)=>{
  const form=host.closest('form');if(!form||form.dataset.comboEditor301||form.dataset.compact200)return;form.dataset.compact200='1';
  let config=null;try{config=JSON.parse(host.dataset.editor192||'null');}catch(_){}
  const mode=form.querySelector('[name=extras_mode]');
  const meta=config?.included195||{};
  const enabled=!!(config?.groups?.length||config?.free_enabled||config?.utensils||config?.notes||meta.side_ids?.length||meta.is_combo||(mode&&mode.value!=='none'));
  const options=document.createElement('div');options.className='nu200-options';host.before(options);
  const modeLabel=mode?.closest('label'),picker=form.querySelector('[data-shared-picker155]');
  if(modeLabel)options.append(modeLabel);if(picker)options.append(picker);options.append(host);
  const question=document.createElement('fieldset');question.className='nu200-question';
  const legend=document.createElement('legend');legend.textContent='Terá adicionais ou acompanhamentos?';question.append(legend);
  const radios=[];
  for(const [value,title] of [['no','Não'],['yes','Sim']]){
   const label=document.createElement('label'),radio=document.createElement('input');radio.type='radio';radio.name='personalization200-'+index;radio.value=value;radio.checked=(value==='yes')===enabled;label.append(radio,document.createTextNode(title));question.append(label);radios.push(radio);
  }
  options.before(question);
  const mealBox=document.createElement('fieldset');mealBox.className='nu200-question';
  const mealLegend=document.createElement('legend');mealLegend.textContent='Esse produto é um lanche ou refeição?';mealBox.append(mealLegend);
  const mealRadios=[];const initialMeal=!!(config?.is_meal317||config?.ingredients?.length);
  for(const [value,title] of [['no','Não'],['yes','Sim']]){const label=document.createElement('label'),radio=document.createElement('input');radio.type='radio';radio.name='meal317-'+index;radio.value=value;radio.checked=(value==='yes')===initialMeal;label.append(radio,document.createTextNode(title));mealBox.append(label);mealRadios.push(radio);}
  const mealFields=document.createElement('div');mealFields.className='nu200-options';const ingredientToggle=[...host.querySelectorAll('label')].find(n=>n.textContent==='Ingredientes do produto')?.querySelector('input');
  const ingredientLabel=ingredientToggle?.closest('label'),ingredientBody=ingredientLabel?.nextElementSibling;
  if(ingredientLabel&&ingredientBody){mealFields.append(ingredientLabel,ingredientBody);ingredientLabel.hidden=true;ingredientLabel.style.setProperty('display','none','important');}
  question.before(mealBox,mealFields);
  function syncMeal(){const meal=mealRadios[1].checked;form.dataset.meal317=String(meal);mealFields.hidden=!meal;if(ingredientToggle){ingredientToggle.checked=meal;ingredientToggle.dispatchEvent(new Event('change'));}sync();}
  mealRadios.forEach(r=>r.addEventListener('change',syncMeal));

  const originalDisabled=new WeakMap();options.querySelectorAll('input,select,textarea,button').forEach(el=>originalDisabled.set(el,el.disabled));
  function sync(){
   const type303=form.querySelector('[data-combo-type303]');const combo=type303?type303.value==='1':['__combos256','combos'].includes(form.querySelector('[name=category]')?.value.toLowerCase());question.hidden=combo;mealBox.hidden=combo;mealFields.hidden=combo||form.dataset.meal317!=='true';ingredientBody?.querySelectorAll('input,button').forEach(n=>n.disabled=combo||form.dataset.meal317!=='true');const simple=radios[0].checked&&!combo;form.dataset.extras317=String(!simple);form.dataset.simple200=String(simple&&form.dataset.meal317!=='true');options.hidden=simple||!!type303&&combo;
   options.querySelectorAll('input,select,textarea,button').forEach(el=>{
    if(el.name==='customization192'||el===mode)return;
    if(simple||!!type303&&combo){if(!el.dataset.disabled200)originalDisabled.set(el,el.disabled);el.dataset.disabled200='1';el.disabled=true;}
    else if(el.dataset.disabled200){el.disabled=!!originalDisabled.get(el);delete el.dataset.disabled200;}
   });
   if(mode){mode.disabled=false;if(!simple)mode.dispatchEvent(new Event('change',{bubbles:true}));}
  }
  form.querySelector('[data-combo-type303]')?.addEventListener('change',sync);radios.forEach(r=>r.addEventListener('change',sync));form.querySelector('[name=category]')?.addEventListener('change',sync);syncMeal();
  form.addEventListener('submit',()=>{if(radios[0].checked&&mode)mode.value='none';},true);
  // Secondary fields remain available without occupying the simple registration form.
  const extra=document.createElement('details');extra.className='nu200-secondary';
  const summary=document.createElement('summary');summary.textContent='Mais informações do produto';extra.append(summary);
  for(const name of ['max_quantity','description','available','featured']){
   const label=form.querySelector('[name="'+name+'"]')?.closest('label');if(label)extra.append(label);
  }
  const category=form.querySelector('[name=category]');function revealCombo(){if(['__combos256','combos'].includes(category?.value.toLowerCase()))extra.open=true;}category?.addEventListener('change',revealCombo);revealCombo();
  if(extra.children.length>1){const save=form.querySelector('button:not([type]),button[type=submit]');if(save)save.before(extra);else form.append(extra);}
 });
})();


