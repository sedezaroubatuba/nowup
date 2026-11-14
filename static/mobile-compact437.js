/* Compact mobile editors: move existing controls, preserving names and handlers. */
(() => {
 'use strict';
 const mobile=window.matchMedia('(max-width: 700px)');
 const make=(tag,cls,text)=>{const n=document.createElement(tag);n.className=cls;if(text)n.textContent=text;return n;};
 function fold(title,nodes){
  const box=make('details','nu437-fold'),summary=make('summary','',title),body=make('div','nu437-body');
  box.append(summary,body);body.append(...nodes);return box;
 }
 function reveal(target){
  for(let p=target.parentElement;p;p=p.parentElement)if(p.tagName==='DETAILS')p.open=true;
 }
 function groupCombo(host){
  if(!host.dataset.sections437){
   host.dataset.sections437='1';
   const nodes=[...host.children],heading=nodes.findIndex(n=>n.tagName==='H3'),manual=nodes.findIndex(n=>n.tagName==='H3'&&n.textContent==='Itens manuais');
   const price=nodes.findIndex(n=>n.classList.contains('nu303-comparison'));
   if(heading>=0&&manual>heading){
    const notices=nodes.slice(0,heading),products=nodes.slice(heading+1,manual),accessories=nodes.slice(manual+1,price<0?nodes.length:price);
    nodes[heading].remove();nodes[manual].remove();
    if(notices.length)host.prepend(fold('Avisos do combo',notices));
    host.append(fold('Produtos e escolhas',products),fold('Itens manuais',accessories));
    if(price>=0)host.append(nodes[price]);
   }
  }
  // Keep item containers and their _value callbacks in place for serialization.
  host.querySelectorAll('.nu301-combo-item').forEach(box=>{
   if(box.querySelector(':scope > .nu437-fold'))return;
   const nodes=[...box.children],legend=nodes.find(n=>n.tagName==='LEGEND');
   const title=()=>legend?.textContent||'Produtos e escolhas';
   const details=fold(title(),nodes.filter(n=>n!==legend));box.append(details);
   const update=()=>{details.firstElementChild.textContent=title();};
   box.addEventListener('input',update);box.addEventListener('change',update);
   // A newly added group must be editable immediately; saved groups start closed.
   details.open=!box.querySelector('.nu301-selected-product');
  });
 }
 function enhance(form){
  if(form.dataset.mobile437)return;form.dataset.mobile437='1';form.classList.add('nu437-form');
  const buckets=new Map(),photos=[],actions=[];
  const add=(title,node)=>{if(!buckets.has(title))buckets.set(title,[]);buckets.get(title).push(node);};
  for(const node of [...form.children]){
   if(node.matches('input[type=hidden],script,template'))continue;
   if(node.matches('button[type=submit],button:not([type])')){actions.push(node);continue;}
   if(node.querySelector('input[type=file]')){photos.push(node);continue;}
   if(node.matches('[data-editor192]')){add('Produtos e personalização',node);continue;}
   if(node.matches('details')){node.classList.add('nu437-fold');continue;}
   const names=[...node.querySelectorAll('[name]')].map(n=>n.name);
   if(node.matches('[name]'))names.push(node.name);
   if(names.some(n=>/price|available|quantity|stock|featured|cold|weight/.test(n)))add('Preço e disponibilidade',node);
   else if(names.some(n=>/^(name|category|description|kind|unit)$/.test(n)))add('Dados do cadastro',node);
   else add('Configurações extras',node);
  }
  const anchor=[...form.children].find(n=>!n.matches('input[type=hidden],script,template'));
  const photo=make('div','nu437-photo');photo.append(...photos);if(photos.length)form.insertBefore(photo,anchor?.parentNode===form?anchor:null);
  for(const [title,nodes] of buckets)form.append(fold(title,nodes));
  if(actions.length){const bar=make('div','nu437-save');bar.append(...actions);form.append(bar);}
  // Native validation must open folded required fields before the browser focuses them.
  form.addEventListener('invalid',event=>reveal(event.target),true);
  form.addEventListener('focusin',event=>reveal(event.target));
 }
 function scan(){
  if(!mobile.matches)return;
  document.querySelectorAll('.pro-dashboard form').forEach(form=>{
   const action=form.getAttribute('action')||'';
   if(/\/excluir(?:$|\?)/.test(action)||!form.querySelector('[name=name], [name=description], [data-editor192]'))return;
   if(!/\/painel\/(?:cardapio|ingredientes|acompanhamentos|adicionais)/.test(action))return;
   enhance(form);
  });
  document.querySelectorAll('.pro-dashboard [data-combo-editor301] [data-editor192]').forEach(groupCombo);
 }
 function start(){
  scan();let queued=false;
  const dashboard=document.querySelector('.pro-dashboard');if(dashboard)new MutationObserver(()=>{if(queued)return;queued=true;queueMicrotask(()=>{queued=false;scan();});}).observe(dashboard,{childList:true,subtree:true});
  mobile.addEventListener('change',()=>{if(mobile.matches)scan();else document.querySelectorAll('.nu437-fold').forEach(n=>n.open=true);});
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
