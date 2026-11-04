/* Run against an isolated panel captured with NOWUP_PANEL322_OUTPUT. */
const {JSDOM}=require(process.env.NOWUP_JSDOM||'jsdom'),fs=require('node:fs'),assert=require('node:assert/strict');
const dom=new JSDOM(fs.readFileSync(process.argv[2],'utf8'),{runScripts:'outside-only',url:'https://nowup.local/painel#lanches-refeicoes322',pretendToBeVisual:true}),w=dom.window,d=w.document;
w.HTMLElement.prototype.scrollIntoView=function(){};w.scrollTo=()=>{};
for(const p of ['combo-editor301.js','custom196.js','meal-groups324.js','compact200.js','pro198.js'])w.eval(fs.readFileSync('static/'+p,'utf8'));
d.dispatchEvent(new w.Event('DOMContentLoaded'));
const food=d.querySelector('#lanches-refeicoes322'),ordinary=d.querySelector('#cardapio'),create=d.querySelector('#novo-produto form');assert.ok(food&&ordinary);
assert.equal(food.hidden,false);assert.equal(ordinary.hidden,true);assert.equal(d.querySelectorAll('#ingredientes320').length,1);assert.ok(d.querySelector('#adicionais').contains(d.querySelector('#ingredientes320')));
assert.equal(ordinary.querySelector('[aria-label=Ingrediente]'),null);assert.equal(ordinary.querySelector('[aria-label="Buscar bebida da loja"]'),null);assert.equal(d.querySelectorAll('[data-step321]').length,0);
assert.ok(create.querySelector('[name=sold_cold]'));assert.ok(create.querySelector('[data-combo-type303]'));assert.ok(create.querySelector('[data-promotion285]'));
for(const meal of food.querySelectorAll('[data-meal-editor322]')){const fold=meal.closest('details');if(fold){fold.open=true;fold.dispatchEvent(new w.Event('toggle'));}assert.equal(meal.querySelectorAll('[data-combo-type303]').length,0);assert.equal(meal.querySelectorAll('[aria-label="Buscar bebida da loja"]').length,0);assert.equal(meal.querySelectorAll('[aria-label="Buscar acompanhamento da loja"]').length,0);const e=new w.Event('submit',{cancelable:true});meal.dispatchEvent(e);assert.equal(e.defaultPrevented,false);assert.equal(new w.FormData(meal).getAll('customization192').length,1);const c=JSON.parse(new w.FormData(meal).get('customization192'));assert.equal(c.is_meal317,true);}
const existing=food.querySelector('[data-meal-card322]');assert.ok(existing);assert.equal(ordinary.querySelector(`[data-pro-product][data-product-id="${existing.dataset.productId}"]`),null);
// Simulate navigation to ordinary products and back, including the registry.
d.querySelector('a[href="#produtos-loja"]').click();assert.equal(ordinary.hidden,false);assert.equal(food.hidden,true);
d.querySelector('a[href="#lanches-refeicoes322"]').click();assert.equal(food.hidden,false);assert.equal(ordinary.hidden,true);
d.querySelector('a[href="#adicionais"]').click();assert.equal(d.querySelector('#adicionais').hidden,false);
dom.window.close();console.log('Rendered merchant panel: separate lists, single configuration per form, no duplicate food controls, preserved normal fields and tab/registry navigation passed.');
