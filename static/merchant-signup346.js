(()=>{'use strict';
 const form=document.getElementById('merchant-signup346');if(!form)return;
 const plan=form.elements.plan,docs=document.getElementById('signup-documents346'),type=form.elements.doc_type,documentField=form.elements.document;
 const other=document.getElementById('signup-other346'),segment=document.getElementById('signup-segment346');
 const cities=JSON.parse(document.getElementById('signup-cities-config346').textContent);
 const simpleOption385=plan.querySelector('[value="cardapio"]'),simpleText385=simpleOption385.textContent;
 function refresh(){
  const fashion=form.elements.business_type.value==='fashion';document.getElementById('fashion-signup385').hidden=!fashion;simpleOption385.textContent=fashion?'Moda e acessórios — R$ 39,90/mês':simpleText385;
  plan.querySelectorAll('option').forEach(o=>{if(['ambos','completo'].includes(o.value))o.disabled=fashion;});
  if(fashion){plan.value='cardapio';form.elements.offer_mode.value='catalog';}
  form.elements.offer_mode.querySelector('[value="menu"]').disabled=fashion;
  const showcase=['ambos','completo'].includes(plan.value);docs.hidden=!showcase;docs.disabled=!showcase;
  type.querySelector('[value="CPF"]').disabled=showcase;
  if(showcase)type.value='CNPJ';documentField.required=showcase;
  document.getElementById('signup-document-note346').textContent=showcase?'(CNPJ obrigatório)':'(opcional)';
  document.getElementById('signup-category-note346').textContent=showcase?'(obrigatória)':'(opcional)';
  form.querySelectorAll('[name="category_choice346"]').forEach(input=>input.required=showcase);
  const manual=other.checked||form.elements.business_type.value==='other';segment.hidden=!manual;form.elements.business_segment346.disabled=!manual;form.elements.business_segment346.required=manual;
  document.getElementById('signup-plan-note346').textContent=showcase?'A vitrine está disponível em '+cities.join(', ')+'. Informe o CNPJ e envie os documentos para análise.':plan.value==='cardapio'?'Cadastro simples: nome da loja, e-mail, celular, senha e endereço. CPF ou CNPJ é opcional. Não precisa enviar documentos.':'Escolha um plano para ver os dados necessários.';
  if(fashion)document.getElementById('signup-plan-note346').textContent='Catálogo Moda e acessórios: R$ 39,90/mês. Atendimento pelo WhatsApp para confirmar disponibilidade, separar, retirar ou entregar. CPF ou CNPJ opcional.';
  form.elements.city.setCustomValidity(showcase&&!cities.includes(form.elements.city.value.trim())?'A vitrine está disponível apenas em '+cities.join(', ')+'. Para outra cidade, escolha só cardápio ou catálogo.':'');
 }
 plan.addEventListener('change',refresh);form.elements.city.addEventListener('input',refresh);
 type.addEventListener('change',refresh);form.querySelectorAll('[name="category_choice346"]').forEach(input=>input.addEventListener('change',refresh));
 form.elements.business_type.addEventListener('change',()=>{if(form.elements.business_type.value==='other')other.checked=true;refresh();});
 window.addEventListener('pageshow',refresh);refresh();
})();
