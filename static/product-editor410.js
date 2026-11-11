/* Organize existing controls without replacing their validation or submission. */
(()=>{'use strict';
 const root=document.querySelector('.pro-dashboard');if(!root||root.classList.contains('fashion-store385'))return;
 const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text)n.textContent=text;if(cls)n.className=cls;return n;};
 const kinds=[['normal','Produto normal','novo-produto'],['weight','Por peso','produtos-peso370'],['combo','Combo','cadastrar-combo'],['meal','Lanche / refeição','novo-lanche322']];
 const kindOf=f=>f.querySelector('[name=sold_by_weight370]')?.value==='1'?'weight':f.dataset.comboEditor301?'combo':f.dataset.mealEditor322?'meal':'normal';
 const fold=(title)=>{const d=el('details',null,'nu410-fold');d.append(el('summary',title));return d;};
 function initialize(){root.querySelectorAll('form.product-form').forEach(form=>{
  if(form.dataset.editor410||!/^\/painel\/cardapio\/produtos(?:\/\d+)?$/.test(new URL(form.action,location.href).pathname)||form.querySelector('[name=size_kind385]'))return;
  const host=form.querySelector('[data-editor192]');if(host&&!host.dataset.ready328)return;
  if(host?._editor321&&!form.dataset.compact200)return;
  form.dataset.editor410='1';form.classList.add('nu410-form');const kind=kindOf(form),name=kinds.find(k=>k[0]===kind)[1];
  const original=[...form.children],heading=el('header',null,'nu410-header'),isEdit=/\/produtos\/\d+$/.test(new URL(form.action,location.href).pathname);
  heading.append(el('span','CADASTRO DE PRODUTOS','nu410-eyebrow'),el('h2',isEdit?'Editar '+name.toLowerCase():'Novo '+name.toLowerCase()),el('p','Preencha os dados e configure as opções deste produto.'));
  if(!isEdit){const nav=el('nav',null,'nu410-types');nav.setAttribute('aria-label','Tipo de produto');kinds.forEach(([key,label,id])=>{const a=el('a',label,key===kind?'is-active':'');a.href='#'+id;a.dataset.nav198='';if(key===kind)a.setAttribute('aria-current','page');nav.append(a);});heading.append(nav);}
  const grid=el('div',null,'nu410-grid'),basic=el('section',null,'nu410-basic'),options=el('section',null,'nu410-options'),footer=el('div',null,'nu410-actions');
  basic.append(el('h3',kind==='combo'?'Dados do combo':kind==='weight'?'Cadastro por quilo':'Dados do produto'));options.append(el('h3',kind==='combo'?'Monte o combo':'Opções deste produto'));
  const extrasHint=el('p','Os adicionais e o limite são exclusivos deste produto. Escolha “Sem adicionais” para não permitir nenhum.','nu410-help');
  const advanced=fold('Mais configurações'),paid=fold('Adicionais pagos'),promotion=fold('Promoção'),related=fold('Leve junto');
  for(const node of original){
   if(node.matches('input[type=hidden]'))continue;
   if(node.matches('button[type=submit],button:not([type])')){footer.append(node);continue;}
   if(node.matches('.nu322-settings')&&node.querySelector('[name=extras_mode]')){node.classList.add('nu410-fold');node.append(extrasHint);options.append(node);continue;}
   if(node.matches('fieldset')&&node.querySelector('[name=extras_mode]')){node.classList.add('nu410-group');node.append(extrasHint);options.append(node);continue;}
   if(node.matches('fieldset')&&node.querySelector('[name=recommend256]')){while(node.firstChild){if(node.firstChild.nodeName==='LEGEND')node.firstChild.remove();else related.append(node.firstChild);}related.open=true;options.append(related);continue;}
   if(node.matches('[data-promotion285]')){node.classList.add('nu410-group');options.append(node);continue;}
   if(node.matches('details')&&node.querySelector('[name=max_quantity]')){
    const summary=node.querySelector(':scope > summary');if(summary)summary.textContent='Mais configurações';node.classList.add('nu410-fold');options.append(node);continue;
   }
   if(node.matches('[data-editor192],[data-switch-combo303],.nu322-section,section,details')){options.append(node);continue;}
   if(node.matches('label')&&node.querySelector('[name=is_combo256]')){const type=node.querySelector('[data-combo-type303]');if(type){node.classList.add('nu410-legacy-type');advanced.append(node);}else options.append(node);continue;}
   if(node.matches('[data-shared-picker155]')||node.querySelector('[name=extras_mode]')){paid.append(node);continue;}
   if(node.querySelector('[name=max_quantity],[name=featured],[name=sold_cold]')){advanced.append(node);continue;}
   if(node.querySelector('[name=recommend256]')){related.append(node);related.open=true;continue;}
   if(node.matches('label')&&node.querySelector('[name=name],[name=category],[name=price],[name=promo_price],[name=photo],[name=description],[name=available]')){basic.append(node);continue;}
   options.append(node);
  }
  if(paid.children.length>1){paid.append(extrasHint);options.append(paid);}
  if(related.children.length>1&&!related.isConnected)options.append(related);
  if(promotion.children.length>1)options.append(promotion);
  if(advanced.children.length>1)options.append(advanced);
  const preview=el('aside',null,'nu410-preview');preview.hidden=true;preview.setAttribute('aria-label','Prévia do produto');
  const previewTitle=el('h3','Prévia do cliente'),photo=el('img'),productName=el('h4'),description=el('p'),price=el('strong',null,'nu410-price'),detail=el('p',null,'nu410-preview-note');photo.alt='Foto do produto';photo.hidden=true;preview.append(previewTitle,photo,productName,description,price,detail,el('p','Prévia visual. Os adicionais e escolhas são conferidos no cardápio.','nu410-help'));
  const previewButton=el('button','Ver prévia','btn soft');previewButton.type='button';previewButton.setAttribute('aria-expanded','false');
  previewButton.onclick=()=>{preview.hidden=!preview.hidden;previewButton.setAttribute('aria-expanded',String(!preview.hidden));update();if(!preview.hidden)preview.scrollIntoView?.({block:'nearest'});};footer.prepend(previewButton);
  const submit=footer.querySelector('button:not([type=button])');if(submit)submit.classList.add('nu410-save');
  let imageURL='';const upload=form.querySelector('[name=photo]');const oldPhoto=upload?.dataset.preview250;if(oldPhoto){photo.src=oldPhoto;photo.hidden=false;}
  upload?.addEventListener('change',()=>{if(imageURL)URL.revokeObjectURL(imageURL);if(upload.files?.[0]){imageURL=URL.createObjectURL(upload.files[0]);photo.src=imageURL;photo.hidden=false;}});
  function update(){productName.textContent=form.querySelector('[name=name]')?.value||'Nome do produto';description.textContent=form.querySelector('[name=description]')?.value||'';const raw=form.querySelector('[name=price]')?.value||'0',value=Number(raw.includes(',')?raw.replace(/\./g,'').replace(',','.'):raw);price.textContent=new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(Number.isFinite(value)?value:0)+(kind==='weight'?' / kg':'');detail.textContent=kind==='weight'?'O cliente escolhe quilos + gramas. Total estimado conforme o peso.':kind==='combo'?'Os itens obrigatórios entram automaticamente. O cliente escolhe somente nos grupos configurados.':'';}
  form.append(heading);grid.append(basic,options);form.append(grid,preview,footer);form.addEventListener('input',update);update();
  form.addEventListener('invalid',event=>{for(let n=event.target.parentElement;n&&n!==form;n=n.parentElement)if(n.tagName==='DETAILS')n.open=true;},true);
 });}
 let scheduled=false;function schedule(){if(scheduled)return;scheduled=true;requestAnimationFrame(()=>{scheduled=false;initialize();});}
 initialize();root.addEventListener('toggle',schedule,true);new MutationObserver(schedule).observe(root,{childList:true,subtree:true});
})();
