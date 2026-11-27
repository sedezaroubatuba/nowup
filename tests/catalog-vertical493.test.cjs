const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('fs');
const {JSDOM}=require('jsdom');
test('vitrine adds one unit, updates counter, obeys max and returns to plus at zero',()=>{
 const item={id:10,name:'Skol',price:4551,max:2,slug:'sede-zero',store:'Sede Zero',options:false};
 const dom=new JSDOM('<header><a data-vitrine-cart data-slug="sede-zero" hidden><span data-vitrine-count></span></a></header><main data-vitrine data-customer=""><p data-vitrine-status></p><div><button data-vitrine-item>+</button></div></main>',{runScripts:'outside-only',url:'https://nowup.local/'});
 const w=dom.window,d=w.document,button=d.querySelector('[data-vitrine-item]');button.dataset.vitrineItem=JSON.stringify(item);
 w.eval(fs.readFileSync('static/vitrine473.js','utf8'));
 const step=d.querySelector('.vitrine-step493'), minus=step.firstElementChild, plus=step.lastElementChild;
 assert.ok(step.hidden);button.click();assert.ok(button.hidden);assert.equal(step.querySelector('span').textContent,'1');plus.click();assert.equal(step.querySelector('span').textContent,'2');assert.equal(d.querySelector('header [data-vitrine-count]').textContent,'2');assert.ok(!d.querySelector('header [data-vitrine-cart]').hidden);assert.ok(plus.disabled);minus.click();minus.click();assert.ok(step.hidden);assert.ok(!button.hidden);assert.ok(d.querySelector('[data-vitrine-cart]').hidden);
 w.close();
});
