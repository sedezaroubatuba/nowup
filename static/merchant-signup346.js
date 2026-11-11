(()=>{'use strict';
 const form=document.getElementById('merchant-signup346');if(!form)return;
 const plan=form.elements.plan,docs=document.getElementById('signup-documents346'),type=form.elements.doc_type,documentField=form.elements.document;
 const other=document.getElementById('signup-other346'),segment=document.getElementById('signup-segment346');
 const cities=['Ubatuba'];
 const simpleOption385=plan.querySelector('[value="cardapio"]'),simpleText385=simpleOption385.textContent;
 function refresh(){
  const fashion=form.elements.business_type.value==='fashion';document.getElementById('fashion-signup385').hidden=!fashion;simpleOption385.textContent=fashion?'Moda e acessórios — R$ 49,90/mês':simpleText385;
  const local=form.elements.city.value.trim().toLocaleLowerCase('pt-BR')==='ubatuba'&&(!form.elements.state?.value||form.elements.state.value==='SP');
  plan.querySelectorAll('option').forEach(o=>{if(['ambos','completo'].includes(o.value)){o.disabled=!local;o.hidden=!local;}});
  if(!local||!plan.value)plan.value=local?'completo':'cardapio';
  if(fashion)form.elements.offer_mode.value='catalog';
  form.elements.offer_mode.querySelector('[value="menu"]').disabled=fashion;
  const showcase=['ambos','completo'].includes(plan.value);docs.hidden=!showcase;docs.disabled=!showcase;
  type.querySelector('[value="CPF"]').disabled=showcase;
  if(showcase)type.value='CNPJ';documentField.required=showcase;
  document.getElementById('signup-document-note346').textContent=showcase?'(CNPJ obrigatório)':'(opcional)';
  document.getElementById('signup-category-note346').textContent=showcase?'(obrigatória)':'(opcional)';
  form.querySelectorAll('[name="category_choice346"]').forEach(input=>input.required=showcase);
  const manual=other.checked||form.elements.business_type.value==='other';segment.hidden=!manual;form.elements.business_segment346.disabled=!manual;form.elements.business_segment346.required=manual;
  document.getElementById('signup-plan-note346').textContent=showcase?'Ubatuba: Cardápio por R$ 49,90/mês + Vitrine por cortesia durante o piloto. Pedidos separados e mesma senha. Informe o CNPJ e envie os documentos para aprovação da Vitrine.':plan.value==='cardapio'?'Cadastro simples: nome da loja, e-mail, celular, senha e endereço. CPF ou CNPJ é opcional. Não precisa enviar documentos.':'Escolha um plano para ver os dados necessários.';

  form.elements.city.setCustomValidity(showcase&&!local?'A vitrine está disponível apenas em '+cities.join(', ')+'. Para outra cidade, escolha só cardápio ou catálogo.':'');
 }
 plan.addEventListener('change',refresh);form.elements.city.addEventListener('input',refresh);form.elements.state?.addEventListener('change',refresh);
 type.addEventListener('change',refresh);form.querySelectorAll('[name="category_choice346"]').forEach(input=>input.addEventListener('change',refresh));
 form.elements.business_type.addEventListener('change',()=>{if(form.elements.business_type.value==='other')other.checked=true;refresh();});
 window.addEventListener('pageshow',refresh);refresh();
})();
