/* Three-step product registration. Hidden steps keep their values and validation. */
(() => {
 'use strict';
 const make=(tag,text,attrs={})=>{const n=document.createElement(tag);if(text)n.textContent=text;Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,v));return n;};
 document.querySelectorAll('.pro-dashboard [data-editor192]').forEach((host,index)=>{
  const form=host.closest('form'),api=host._editor321;if(!form||!api||form.dataset.comboEditor301||form.dataset.compact200)return;
  form.dataset.compact200='321';form.dataset.extras317='true';form.dataset.simple200='false';
  let config={};try{config=JSON.parse(host.dataset.editor192||'{}');}catch(_){}
  const submit=form.querySelector('button[type=submit],button:not([type])');if(!submit)return;submit.type='submit';
  const nav=make('nav','',{'aria-label':'Etapas do cadastro',class:'nu321-steps full'}),panels=['Produto','Ingredientes','Complementos'].map((title,i)=>{const panel=make('section','',{'data-step321':String(i),class:'nu321-panel full'});panel.append(make('h3',title));return panel;});
  const original=[...form.children];form.prepend(nav,...panels);
  for(const child of original){if(child!==submit)panels[0].append(child);}
  const extras=make('details'),extrasTitle=make('summary','Adicionais pagos');extras.append(extrasTitle);
  const mode=api.mode,modeLabel=mode?.closest('label'),picker=form.querySelector('[data-shared-picker155]');if(modeLabel)extras.append(modeLabel);if(picker)extras.append(picker);extras.append(api.extras);
  extras.open=!!(mode&&mode.value!=='none');panels[2].append(extras,host);const bundle=form.querySelector('[data-switch-combo303]');if(bundle)panels[2].append(bundle);
  api.heading.hidden=true;host.querySelectorAll(':scope > h3').forEach(n=>n.hidden=true);
  const ingredientLabel=api.ing.toggle.closest('label');ingredientLabel.hidden=true;
  panels[1].append(ingredientLabel,api.ing.body);
  const ingredientChoice=make('fieldset'),legend=make('legend','Como deseja adicionar os ingredientes?');ingredientChoice.append(legend);
  const choices=[];const initial=config.ingredients?.length?(config.ingredients.some(i=>i.ingredient_id320)?'catalog':'manual'):'description';
  for(const [value,title] of [['manual','Digitar manualmente'],['catalog','Selecionar cadastrados'],['description','Informar apenas na descrição']]){const label=make('label'),radio=make('input','',{type:'radio',name:'ingredients321-'+index,value});radio.checked=value===initial;label.append(radio,document.createTextNode(title));ingredientChoice.append(label);choices.push(radio);}
  panels[1].insertBefore(ingredientChoice,ingredientLabel);
  const hint=make('p','Os ingredientes são opcionais. Você também pode descrevê-los no produto; o cliente escreve o que deseja retirar na observação.');panels[1].insertBefore(hint,ingredientChoice);
  const searchWrap=make('div');searchWrap.append(api.ingredientLink320,api.ingredientSearch320,api.ingredientPicker320);api.ing.body.prepend(searchWrap);
  const mealBox=make('fieldset','',{class:'nu200-question'});mealBox.append(make('legend','Esse produto é um lanche ou refeição?'));
  const mealRadios=[];for(const [value,title] of [['no','Não'],['yes','Sim']]){const label=make('label'),radio=make('input','',{type:'radio',name:'meal317-'+index,value});radio.checked=(value==='yes')===!!(config.is_meal317||config.ingredients?.length);label.append(radio,document.createTextNode(title));mealBox.append(label);mealRadios.push(radio);}panels[0].append(mealBox);
  // A meal uses itself as the main item; the independent bundle editor stays available for other products.
  const type=form.querySelector('[data-combo-type303]'),typeLabel=type?.closest('label');if(typeLabel)panels[2].prepend(typeLabel);
  const principal=make('p','',{'data-main321':''});api.comboLabel.before(principal);
  const advanced=make('details'),advancedTitle=make('summary','Outras opções (opcional)');advanced.append(advancedTitle);
  const sideHeading=api.shared.querySelector('h3'),sideHint=sideHeading?.nextElementSibling;
  for(const n of [sideHeading,sideHint,api.sidePicker,api.sideCountLabel,api.requiredLabel,api.groups.toggle.closest('label'),api.groups.body,api.utensils.closest('label')])if(n)advanced.append(n);
  advanced.open=!!(config.included195?.side_ids?.length||config.groups?.some(g=>!['side195','drink195'].includes(g.id))||config.utensils);
  host.append(advanced);api.manualBox321.before(api.shared);api.notes.checked=config.notes!==false||!!config.is_meal317||!Object.keys(config).length;
  api.notes.closest('label').hidden=true;
  // Keep the description visible on the first step, including the description-only ingredient path.
  const description=form.querySelector('[name=description]');if(description){description.required=false;description.placeholder='Ex.: pão, alface, tomate, queijo e hambúrguer. O cliente pode pedir alterações na observação.';const label=description.closest('label');if(label)panels[0].insertBefore(label,mealBox);}
  const info=make('details'),infoTitle=make('summary','Mais informações do produto');info.append(infoTitle);
  for(const name of ['max_quantity','available','featured','sold_cold']){const label=form.querySelector('[name="'+name+'"]')?.closest('label');if(label)info.append(label);}if(info.children.length>1)panels[0].append(info);
  function syncIngredients(){const meal=mealRadios[1].checked,selected=choices.find(r=>r.checked)?.value;form.dataset.meal317=String(meal);if(meal)api.notes.checked=true;api.ing.toggle.checked=meal&&selected!=='description';api.ing.sync();searchWrap.hidden=selected!=='catalog';api.addIngredient.hidden=selected!=='manual';api.ing.body.querySelectorAll('[aria-label=Ingrediente]').forEach(n=>{n.required=false;n.disabled=!api.ing.toggle.checked;});}
  function syncMeal(){const meal=mealRadios[1].checked;if(meal&&type?.value==='1'){type.value='0';type.dispatchEvent(new Event('change',{bubbles:true}));}if(typeLabel)typeLabel.hidden=meal;principal.textContent='Principal: '+(form.querySelector('[name=name]')?.value.trim()||'o próprio produto');principal.hidden=!meal;syncIngredients();}
  choices.forEach(r=>r.addEventListener('change',syncIngredients));mealRadios.forEach(r=>r.addEventListener('change',syncMeal));form.querySelector('[name=name]')?.addEventListener('input',syncMeal);
  api.addIngredient.addEventListener('click',syncIngredients);api.ingredientPicker320.addEventListener('click',syncIngredients);
  let current=0;const back=make('button','Voltar',{type:'button',class:'btn soft'}),next=make('button','Continuar',{type:'button',class:'btn primary'}),actions=make('div','',{class:'nu321-actions full'});actions.append(back,next,submit);form.append(actions);
  const buttons=panels.map((p,i)=>{const button=make('button',(i+1)+' · '+['Produto','Ingredientes','Complementos'][i],{type:'button'});button.onclick=()=>go(i);nav.append(button);return button;});
  function show(i){current=i;panels.forEach((p,n)=>p.hidden=n!==i);buttons.forEach((b,n)=>{b.setAttribute('aria-current',n===i?'step':'false');b.classList.toggle('active',n===i);});back.hidden=i===0;next.hidden=i===2;submit.hidden=i!==2;}
  function validStep(){for(const input of panels[current].querySelectorAll('input,select,textarea'))if(!input.disabled&&!input.checkValidity()){input.reportValidity();return false;}return true;}
  function go(i){if(i>current&&!validStep())return;show(i);}
  next.onclick=()=>go(Math.min(2,current+1));back.onclick=()=>go(Math.max(0,current-1));
  form.addEventListener('invalid',e=>{const step=e.target.closest('[data-step321]');if(step)show(Number(step.dataset.step321));},true);
  form.addEventListener('submit',e=>{if(current!==2){e.preventDefault();go(Math.min(2,current+1));}},true);
  syncMeal();show(0);
 });
})();
