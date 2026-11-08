/* Async dialogs preserve native form validation, submitter and change events. */
(()=>{'use strict';
let queue=Promise.resolve();
function open(options){const job=queue.then(()=>new Promise(resolve=>{
 const previous=document.activeElement,d=document.createElement('dialog');d.className='nu-dialog';d.setAttribute('aria-labelledby','nu-dialog-title');
 const brand=document.createElement('div');brand.className='nu-dialog-brand';brand.textContent='NowUp';
 const title=document.createElement('h2');title.id='nu-dialog-title';title.textContent=options.title||'NowUp';d.append(brand,title);
 let field;const finish=value=>{d.close();d.remove();if(previous?.isConnected)previous.focus({preventScroll:true});resolve(value);};
 if(options.message){const text=document.createElement('p');text.id='nu-dialog-message';text.textContent=String(options.message);d.setAttribute('aria-describedby',text.id);d.append(text);}
 if(options.input){field=document.createElement('textarea');field.value=options.value||'';field.required=!!options.required;field.setAttribute('aria-label',String(options.message||options.title));d.append(field);}
 if(options.select){const select=options.select;const list=document.createElement('div');list.className='nu-dialog-options';list.setAttribute('role','group');list.setAttribute('aria-label',title.textContent);
  let search;if(select.options.length>8){search=document.createElement('input');search.type='search';search.placeholder='Buscar opção';search.setAttribute('aria-label','Buscar opção');d.append(search);}
  const empty=document.createElement('p');empty.className='nu-dialog-empty';empty.textContent='Nenhuma opção encontrada.';empty.hidden=true;
  [...select.options].forEach(option=>{if(option.hidden)return;const button=document.createElement('button');button.type='button';button.className='nu-dialog-option';button.textContent=(option.parentElement.tagName==='OPTGROUP'?option.parentElement.label+' · ':'')+option.textContent;button.disabled=option.disabled||(option.parentElement.tagName==='OPTGROUP'&&option.parentElement.disabled);button.setAttribute('aria-pressed',String(option.selected));button.addEventListener('click',()=>finish(option));list.append(button);});d.append(list,empty);
  search?.addEventListener('input',()=>{const norm=s=>s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('pt-BR');let count=0;for(const b of list.children){b.hidden=!norm(b.textContent).includes(norm(search.value));if(!b.hidden)count++;}empty.hidden=!!count;});
 }
 const actions=document.createElement('div');actions.className='nu-dialog-actions';
 if(options.cancel!==false){const cancel=document.createElement('button');cancel.type='button';cancel.className='nu-dialog-secondary';cancel.textContent='Cancelar';cancel.addEventListener('click',()=>finish(null));actions.append(cancel);}
 if(!options.select){const ok=document.createElement('button');ok.type='button';ok.textContent=options.confirm||'OK';ok.addEventListener('click',()=>{if(field&&options.required&&!field.value.trim()){field.setCustomValidity('Informe o motivo para continuar.');field.reportValidity();return;}finish(field?field.value:true);});field?.addEventListener('input',()=>field.setCustomValidity(''));actions.append(ok);}
 d.append(actions);d.addEventListener('cancel',e=>{e.preventDefault();finish(null);});document.body.append(d);d.showModal();(field||d.querySelector('input')||d.querySelector('[aria-pressed="true"]')||actions.querySelector('button'))?.focus();
}));queue=job.catch(()=>{});return job;}
window.NowUpDialog={alert:message=>open({message,title:'Aviso',cancel:false}),confirm:message=>open({message,title:'Confirmar ação',confirm:'Confirmar'}),prompt:(message,value='',extra={})=>open({message,value,input:true,title:'Confira os dados',...extra})};
window.alert=message=>{window.NowUpDialog.alert(message);};
const waiting=new WeakSet(),approved=new WeakSet();
document.addEventListener('submit',async event=>{const form=event.target;if(approved.has(form)){approved.delete(form);return;}
 const action=event.submitter?.getAttribute('formaction')||form.action;let logout=false;try{logout=new URL(action,location.href).pathname.replace(/\/+$/,'')==='/sair';}catch(_){}
 const message=form.dataset.nuConfirm||(logout?'Tem certeza que deseja sair da sua conta do NowUp?':form.matches('form[action*="/excluir"],form[data-confirm-delete]')?'Você realmente deseja excluir? Essa ação não poderá ser desfeita.':null);if(!message)return;
 event.preventDefault();event.stopImmediatePropagation();if(waiting.has(form))return;waiting.add(form);const result=await window.NowUpDialog.confirm(message);waiting.delete(form);if(result&&form.isConnected){approved.add(form);form.requestSubmit(event.submitter||undefined);}else form.dispatchEvent(new Event('nowup:cancel'));
},true);
const supported=s=>s instanceof HTMLSelectElement&&!s.multiple&&s.size<=1&&!s.disabled&&!s.hasAttribute('data-native-select');
let selecting=null;
function selectTitle(s){const label=s.labels?.[0]?.cloneNode(true);label?.querySelectorAll('select,input,textarea,button').forEach(n=>n.remove());return label?.textContent.trim()||s.getAttribute('aria-label')||'Selecione uma opção';}
async function selectOption(s){if(selecting)return;selecting=s;try{const option=await open({title:selectTitle(s),select:s});if(option&&s.isConnected&&!s.disabled&&option.parentElement&&s.contains(option)&&!option.disabled&&s.selectedIndex!==option.index){s.selectedIndex=option.index;s.dispatchEvent(new Event('input',{bubbles:true}));s.dispatchEvent(new Event('change',{bubbles:true}));}}finally{selecting=null;}}
document.addEventListener('mousedown',e=>{if(supported(e.target))e.preventDefault();},true);
document.addEventListener('click',e=>{if(!supported(e.target))return;e.preventDefault();e.stopImmediatePropagation();selectOption(e.target);},true);
document.addEventListener('keydown',e=>{if(supported(e.target)&&['Enter',' ','ArrowDown','ArrowUp'].includes(e.key)){e.preventDefault();e.stopImmediatePropagation();selectOption(e.target);}},true);
})();
