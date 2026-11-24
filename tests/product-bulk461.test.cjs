const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {JSDOM}=require('jsdom');
const source=fs.readFileSync('static/product-bulk460.js','utf8');
const records=[
 {id:12,name:'Skol Lata 350ml',category:'Cervejas',price:390,parent:0,subcategory:7},
 {id:14,name:'Skol Lata 473ml',category:'Cervejas',price:590,parent:0},
 {id:21,name:'Gelo de coco',category:'Gelo',price:250,parent:0}
];
function setup(products=records){
 const html=`<section class="nu460-batch"><form data-bulk-form460 action="/painel/todos-produtos/lote">
 <select data-bulk-filter465><option value="">Todas</option></select><input data-bulk-search460 type="search"><div data-bulk-results460></div>
 <span data-bulk-count460></span><div data-bulk-selected460></div><div data-bulk-ids460></div>
 <select data-bulk-operation460 name="operation"><option value="related">Leve Junto</option><option value="prices">Preços</option><option value="category">Categoria</option></select>
 <select data-bulk-category460><option value="">Selecione</option><option value="Cervejas">Cervejas</option></select>
 <select data-bulk-subcategory460><option value="0">Sem subcategoria</option><option value="7" data-parent="Cervejas">Latas</option><option value="8" data-parent="Cervejas">Fardos</option></select>
 <input data-bulk-target-search460><select data-bulk-target460 name="target_id"></select>
 <div data-bulk-price-fields460></div><input data-bulk-prices-json460 name="prices_json">
 <p data-bulk-status460></p><button data-bulk-submit460 type="submit"></button>
 <button type="button" data-bulk-clear460>Limpar</button>
 <div data-bulk-mode460="related"></div><div data-bulk-mode460="category"></div>
 <div data-bulk-mode460="prices"></div><div data-bulk-mode460="availability"></div>
 </form></section><script id="nu455-product-names" type="application/json">${JSON.stringify(products)}</script>`;
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
  assert.equal(doc.querySelector('[data-bulk-count460]').textContent,'1 de 20 produtos selecionados');
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

test('source category limits search, keeps the selection and previews subcategory changes',async()=>{
 const dom=setup();
 try{
  const w=dom.window,d=w.document;
  const pick=(selector,value)=>{
   const el=d.querySelector(selector);el.value=value;el.dispatchEvent(new w.Event('change',{bubbles:true}));
  };
  pick('[data-bulk-filter465]','cervejas');
  assert.equal(d.querySelectorAll('.nu460-result').length,2);
  assert.equal(d.querySelector('.nu465-assigned').textContent,'✓ Latas');
  d.querySelector('.nu460-result input').click();
  pick('[data-bulk-filter465]','gelo');
  assert.equal(d.querySelectorAll('.nu460-result').length,1);
  assert.equal(d.querySelectorAll('[name=selected_ids]').length,1);
  pick('[data-bulk-operation460]','category');
  pick('[data-bulk-category460]','Cervejas');
  pick('[data-bulk-subcategory460]','8');
  let preview;
  w.NowUpDialog={confirm:async (...args)=>{preview=args;return false;}};
  d.querySelector('form').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));
  assert.match(preview[0],/Cervejas \/ Latas → Cervejas \/ Fardos/);
  assert.match(preview[1].warning,/1 produto/);
  assert.equal(d.querySelectorAll('[name=selected_ids]').length,1);
 }finally{dom.window.close();}
});
test('selecting twenty products leaves the twenty-first unavailable',()=>{
 const products=Array.from({length:21},(_,i)=>({id:i+1,name:'Produto '+i,category:'Mercearia',price:100}));
 const dom=setup(products);
 try{
  const d=dom.window.document;
  for(let i=0;i<20;i++)d.querySelectorAll('.nu460-result input')[i].click();
  assert.equal(d.querySelectorAll('[name=selected_ids]').length,20);
  assert.equal(d.querySelectorAll('.nu460-result input')[20].disabled,true);
 }finally{dom.window.close();}
});
