const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {JSDOM}=require('jsdom');
const source=fs.readFileSync('static/product-bulk460.js','utf8');
const records=[
 {id:12,name:'Skol Lata 350ml',category:'Cervejas',price:390,parent:0},
 {id:14,name:'Skol Lata 473ml',category:'Cervejas',price:590,parent:0},
 {id:21,name:'Gelo de coco',category:'Gelo',price:250,parent:0}
];
function setup(){
 const html=`<section class="nu460-batch"><form data-bulk-form460 action="/painel/todos-produtos/lote">
 <input data-bulk-search460 type="search"><div data-bulk-results460></div>
 <span data-bulk-count460></span><div data-bulk-selected460></div><div data-bulk-ids460></div>
 <select data-bulk-operation460 name="operation"><option value="related">Leve Junto</option><option value="prices">Preços</option></select>
 <select data-bulk-category460><option value="">Selecione</option></select>
 <select data-bulk-subcategory460><option value="0">Sem subcategoria</option></select>
 <input data-bulk-target-search460><select data-bulk-target460 name="target_id"></select>
 <div data-bulk-price-fields460></div><input data-bulk-prices-json460 name="prices_json">
 <p data-bulk-status460></p><button data-bulk-submit460 type="submit"></button>
 <button type="button" data-bulk-clear460>Limpar</button>
 <div data-bulk-mode460="related"></div><div data-bulk-mode460="category"></div>
 <div data-bulk-mode460="prices"></div><div data-bulk-mode460="availability"></div>
 </form></section><script id="nu455-product-names" type="application/json">${JSON.stringify(records)}</script>`;
 const dom=new JSDOM(html,{url:'https://nowupbrasil.com/painel/todos-produtos',runScripts:'outside-only'});
 dom.window.eval(source);
 return dom;
}
test('searching Skol actually renders both matching selectable products',()=>{
 const dom=setup();try{
  const doc=dom.window.document,search=doc.querySelector('[data-bulk-search460]');
  search.value='Skol';search.dispatchEvent(new dom.window.Event('input',{bubbles:true}));
  const rows=doc.querySelectorAll('.nu460-result');
  assert.equal(rows.length,2);
  assert.equal(rows[0].querySelector('strong').textContent,'Skol Lata 350ml');
  assert.equal(rows[1].querySelector('strong').textContent,'Skol Lata 473ml');
  rows[0].querySelector('input[type=checkbox]').click();
  assert.equal(doc.querySelector('[data-bulk-count460]').textContent,'1 de 10 produtos selecionados');
  search.value='Gelo';search.dispatchEvent(new dom.window.Event('input',{bubbles:true}));
  assert.equal(doc.querySelectorAll('.nu460-result').length,1);
  assert.equal(doc.querySelectorAll('input[name=selected_ids]').length,1);
  // The Leve Junto target chooser must also populate from the same catalogue.
  const targetSearch=doc.querySelector('[data-bulk-target-search460]');
  targetSearch.value='Gelo';
  targetSearch.dispatchEvent(new dom.window.Event('input',{bubbles:true}));
  const options=[...doc.querySelector('[data-bulk-target460]').options];
  assert(options.some(option=>option.textContent.includes('Gelo de coco')));
  targetSearch.value='Skol';
  targetSearch.dispatchEvent(new dom.window.Event('input',{bubbles:true}));
  assert(options.length>0);
  assert([...doc.querySelector('[data-bulk-target460]').options].some(option=>option.textContent.includes('Skol Lata 473ml')));
  // Select a second product from the updated source search; retain first selection.
  doc.querySelector('.nu460-result input').click();
  assert.equal(doc.querySelectorAll('input[name=selected_ids]').length,2);
 }finally{dom.window.close();}
});
