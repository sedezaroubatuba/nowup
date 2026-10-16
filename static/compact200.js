/* Compact product editor: advanced fields are optional and existing values survive until saved. */
(() => {
 'use strict';
 document.querySelectorAll('.pro-dashboard [data-editor192]').forEach((host,index)=>{
  const form=host.closest('form');if(!form||form.dataset.compact200)return;form.dataset.compact200='1';
  let config=null;try{config=JSON.parse(host.dataset.editor192||'null');}catch(_){}
  const mode=form.querySelector('[name=extras_mode]');
  const meta=config?.included195||{};
  const enabled=!!(config?.ingredients?.length||config?.groups?.length||config?.free_enabled||config?.utensils||config?.notes||meta.side_ids?.length||meta.is_combo||(mode&&mode.value!=='none'));
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
  const originalDisabled=new WeakMap();options.querySelectorAll('input,select,textarea,button').forEach(el=>originalDisabled.set(el,el.disabled));
  function sync(){
   const simple=radios[0].checked;form.dataset.simple200=String(simple);options.hidden=simple;
   options.querySelectorAll('input,select,textarea,button').forEach(el=>{
    if(el.name==='customization192'||el===mode)return;
    if(simple){if(!el.dataset.disabled200)originalDisabled.set(el,el.disabled);el.dataset.disabled200='1';el.disabled=true;}
    else if(el.dataset.disabled200){el.disabled=!!originalDisabled.get(el);delete el.dataset.disabled200;}
   });
   if(mode){mode.disabled=false;if(!simple)mode.dispatchEvent(new Event('change',{bubbles:true}));}
  }
  radios.forEach(r=>r.addEventListener('change',sync));sync();
  form.addEventListener('submit',()=>{if(form.dataset.simple200==='true'&&mode)mode.value='none';},true);
  // Secondary fields remain available without occupying the simple registration form.
  const extra=document.createElement('details');extra.className='nu200-secondary';
  const summary=document.createElement('summary');summary.textContent='Mais informações do produto';extra.append(summary);
  for(const name of ['promo_price','max_quantity','description','available','featured']){
   const label=form.querySelector('[name="'+name+'"]')?.closest('label');if(label)extra.append(label);
  }
  if(extra.children.length>1){const save=form.querySelector('button:not([type]),button[type=submit]');if(save)save.before(extra);else form.append(extra);}
 });
})();
