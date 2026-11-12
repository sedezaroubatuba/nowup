// Use real select/option nodes: this form now changes options by city and segment.
const {JSDOM}=require('jsdom'),fs=require('node:fs'),assert=require('node:assert/strict');
const dom=new JSDOM(`<form id="merchant-signup346"><select name="plan"><option value="">Escolha</option><option value="cardapio">Cardápio</option><option value="ambos">Vitrine anterior</option><option value="completo">Cardápio e vitrine</option></select><select name="doc_type"><option value="CPF">CPF</option><option value="CNPJ">CNPJ</option></select><input name="document"><input name="city" value="Ubatuba"><select name="state"><option>SP</option><option>RJ</option></select><select name="business_type"><option value="store">Loja</option><option value="fashion">Moda</option><option value="other">Outro</option></select><select name="offer_mode"><option value="menu">Cardápio</option><option value="catalog">Catálogo</option></select><input type="radio" name="category_choice346" value="1" checked><input id="signup-other346" type="radio" name="category_choice346" value="other"><div id="signup-segment346"><input name="business_segment346"></div><fieldset id="signup-documents346"></fieldset><div id="fashion-signup385"></div><span id="signup-document-note346"></span><span id="signup-category-note346"></span><span id="signup-plan-note346"></span></form>`,{url:'https://test.invalid/cadastro',runScripts:'outside-only'});
const w=dom.window,f=w.document.querySelector('form'),e=f.elements,docs=w.document.getElementById('signup-documents346'),other=w.document.getElementById('signup-other346');
const set=(name,value,kind='change')=>{e[name].value=value;e[name].dispatchEvent(new w.Event(kind,{bubbles:true}));};
try{
 w.eval(fs.readFileSync('static/merchant-signup346.js','utf8'));
 assert.equal(e.plan.value,'completo');assert(!docs.hidden&&e.document.required);
 set('plan','cardapio');assert(docs.hidden&&docs.disabled);assert(!e.document.required);
 set('doc_type','CPF');set('city','São Sebastião','input');assert.equal(e.plan.value,'cardapio');assert.equal(e.city.validationMessage,'');assert.equal(e.doc_type.value,'CPF');assert(e.plan.querySelector('[value=completo]').disabled);
 set('city','Ubatuba','input');set('plan','completo');assert(!docs.hidden&&!docs.disabled&&e.document.required);assert.equal(e.doc_type.value,'CNPJ');assert(e.doc_type.querySelector('[value=CPF]').disabled);
 set('plan','cardapio');assert(docs.hidden&&docs.disabled&&!e.document.required);assert(!e.doc_type.querySelector('[value=CPF]').disabled);
 other.checked=true;other.dispatchEvent(new w.Event('change',{bubbles:true}));assert(e.business_segment346.required&&!e.business_segment346.disabled);
 set('business_type','fashion');assert.equal(e.offer_mode.value,'catalog');assert(e.offer_mode.querySelector('[value=menu]').disabled);assert(!w.document.getElementById('fashion-signup385').hidden);
 set('state','RJ');assert.equal(e.plan.value,'cardapio');assert(e.plan.querySelector('[value=completo]').hidden);
 console.log('Cadastro validado com DOM real: planos por cidade, CPF opcional no Cardápio, CNPJ/documentos na Vitrine e catálogo de moda.');
}finally{w.close();}
