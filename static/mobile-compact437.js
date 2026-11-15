/* Mobile-only basic form with optional advanced settings. Existing controls stay live. */
(() => {
 'use strict';
 const mobile=window.matchMedia('(max-width: 700px)'),states=new Map(),groups=new Map();
 const make=(tag,cls,text)=>{const n=document.createElement(tag);n.className=cls;if(text)n.textContent=text;return n;};
 function move(node,parent,state){const mark=document.createComment('mobile layout');node.before(mark);state.moves.push([node,mark]);parent.append(node);}
 function fold(title){const box=make('details','nu437-fold'),summary=make('summary','',title),body=make('div','nu437-body');box.append(summary,body);return [box,body];}
 function reveal(target){for(let p=target.parentElement;p;p=p.parentElement)if(p.tagName==='DETAILS')p.open=true;}
 function enhance(form){
  if(states.has(form))return;
  const state={moves:[],generated:[],classes:[]};states.set(form,state);form.classList.add('nu437-form','nu438-basic');
  const [advanced,body]=fold('Mais configurações'),photo=make('div','nu437-photo'),bar=make('div','nu437-save');
  state.generated.push(advanced,photo,bar);
  const children=[...form.children];
  for(const node of children){
   if(node.matches('input[type=hidden],script,template'))continue;
   if(node.matches('button[type=submit],button:not([type])')){move(node,bar,state);continue;}
   if(node.querySelector('input[type=file]')){move(node,photo,state);continue;}
   const fields=[...node.querySelectorAll('input,select,textarea')],basic=node.matches('label')&&fields.length&&fields.every(n=>/^(name|category|price|description|available|sold_cold|unit|kind)$/.test(n.name));
   if(basic){
    const wide=fields.some(n=>/^(name|description)$/.test(n.name));node.classList.add(wide?'nu438-wide':'nu438-half');state.classes.push(node);continue;
   }
   move(node,body,state);
  }
  if(photo.children.length)form.prepend(photo);
  if(body.children.length)form.append(advanced);
  if(bar.children.length)form.append(bar);
  state.invalid=event=>reveal(event.target);form.addEventListener('invalid',state.invalid,true);form.addEventListener('focusin',state.invalid);
 }
 function compactGroups(host){
  host.querySelectorAll('.nu301-combo-item').forEach(box=>{
   if(groups.has(box))return;
   const state={moves:[],generated:[]},legend=box.querySelector(':scope > legend'),[details,body]=fold('');
   groups.set(box,state);state.generated.push(details);
   [...box.children].filter(n=>n!==legend).forEach(n=>move(n,body,state));box.append(details);
   const summary=details.firstElementChild;
   function update(){
    const name=box.querySelector('[aria-label="Nome do grupo de escolhas"]')?.value.trim(),count=box.querySelector('[aria-label="Unidades incluídas neste grupo"]')?.value||'1';
    const first=box.querySelector('.nu301-selected-product strong')?.textContent;
    const text=(name||first||legend?.textContent||'Novo grupo')+' · '+count+' un. — Editar';
    if(summary.textContent!==text)summary.textContent=text;
   }
   state.update=update;box.addEventListener('input',update);box.addEventListener('change',update);update();
   details.open=!box.querySelector('.nu301-selected-product')||body.contains(document.activeElement);
  });
 }
 function restore(state){for(const [node,mark] of state.moves.reverse()){if(mark.parentNode){mark.replaceWith(node);}}state.generated.forEach(n=>n.remove());}
 function desktop(){
  for(const [box,state] of groups){box.removeEventListener('input',state.update);box.removeEventListener('change',state.update);restore(state);}groups.clear();
  for(const [form,state] of states){restore(state);form.classList.remove('nu437-form','nu438-basic');state.classes.forEach(n=>n.classList.remove('nu438-wide','nu438-half'));form.removeEventListener('invalid',state.invalid,true);form.removeEventListener('focusin',state.invalid);}states.clear();
 }
 function scan(){
  if(!mobile.matches)return;
  document.querySelectorAll('.pro-dashboard form').forEach(form=>{
   const action=form.getAttribute('action')||'';
   if(/\/excluir(?:$|\?)/.test(action)||!form.querySelector('[name=name], [name=description], [data-editor192]'))return;
   if(/\/painel\/(?:cardapio|ingredientes|acompanhamentos|adicionais)/.test(action))enhance(form);
  });
  document.querySelectorAll('.pro-dashboard [data-combo-editor301] [data-editor192],.pro-dashboard [data-switch-combo303]').forEach(compactGroups);
 }
 function start(){
  scan();let queued=false;const dashboard=document.querySelector('.pro-dashboard');
  if(dashboard)new MutationObserver(()=>{if(queued)return;queued=true;queueMicrotask(()=>{queued=false;scan();});}).observe(dashboard,{childList:true,subtree:true});
  mobile.addEventListener('change',()=>mobile.matches?scan():desktop());
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
