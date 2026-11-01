const {JSDOM}=require(process.env.NOWUP_JSDOM||'jsdom');
const fs=require('node:fs'),assert=require('node:assert/strict');
const dom=new JSDOM(`<div class="pro-dashboard" data-merchant228><aside class="pro-sidebar"><a href="#bairros-entrega265">Bairros</a></aside><main><section id="inicio"></section><section id="configuracoes"><a href="#entrega-pagamento">Pagamento</a><a href="#exibicao-produtos">Exibição</a></section><section id="cardapio"><details id="entrega-pagamento"><summary>Pagamento</summary></details><section id="exibicao-produtos"></section></section><section id="combos-loja"><input data-search-combos301><div data-combos-list301><details data-combo-card301 data-name="Whisky e gelo"></details><details data-combo-card301 data-name="Cerveja e carvão"></details></div></section></main></div>`,{url:'https://nowup.local/painel',runScripts:'outside-only',pretendToBeVisual:true});
const w=dom.window;w.HTMLElement.prototype.scrollIntoView=function(){};w.scrollTo=()=>{};
for(const file of ['static/pro-panel-menu.js','static/pro198.js'])w.eval(fs.readFileSync(file,'utf8'));
w.document.dispatchEvent(new w.Event('DOMContentLoaded'));
for(const key of ['entrega-pagamento','exibicao-produtos','bairros-entrega265']){
 w.document.querySelector(`a[href="#${key}"]`).click();assert.equal(w.location.hash,'#'+key);assert.equal(w.document.getElementById('cardapio').hidden,false);
}
assert.equal(w.document.getElementById('entrega-pagamento').open,true);
assert.ok(w.document.querySelector('.show-full-dashboard'));
const search=w.document.querySelector('[data-search-combos301]'),cards=[...w.document.querySelectorAll('[data-combo-card301]')];
function query(value){search.value=value;search.dispatchEvent(new w.Event('input'));}
query('CARVAO');assert.deepEqual(cards.map(c=>c.hidden),[true,false]);query('inexistente');assert.ok(cards.every(c=>c.hidden));assert.equal(w.document.querySelector('[role=status]').hidden,false);query('');assert.ok(cards.every(c=>!c.hidden));
w.close();console.log('Panel navigation and combo search passed.');
