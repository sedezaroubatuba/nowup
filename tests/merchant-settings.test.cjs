const {JSDOM}=require(process.env.NOWUP_JSDOM||'jsdom');
const fs=require('node:fs'),assert=require('node:assert/strict');
const dom=new JSDOM(fs.readFileSync(0,'utf8'),{url:'https://nowup.local/painel',runScripts:'outside-only',pretendToBeVisual:true});
const w=dom.window,d=w.document;
w.HTMLElement.prototype.scrollIntoView=function(){};w.scrollTo=()=>{};
const profile=d.getElementById('perfil'),catalog=d.getElementById('cardapio'),weight=d.getElementById('peso-loja');
for(const id of ['horarios','identidade','entrega-pagamento','exibicao-produtos','bairros-entrega265','cardapio-independente','plano']){
 assert.ok(profile.contains(d.getElementById(id)),id+' must be in My Store');
 assert.equal(d.querySelectorAll('#'+id).length,1,id+' must not be duplicated');
}
for(const name of ['display_name','pix_key','pix_key_type','minimum_order'])assert.ok(profile.querySelector('[name="'+name+'"]'));
assert.equal(catalog.querySelector('[name="pix_key"]'),null);
assert.ok(weight.contains(d.getElementById('produtos-peso370')));
assert.equal(catalog.querySelector('#produtos-peso370'),null);
assert.ok(d.getElementById('adicionais').contains(d.getElementById('acompanhamentos-combos')));
const normal=d.querySelector('[data-pro-product][data-name="Produto comum teste"]');
const weighted=d.querySelector('[data-pro-product][data-name="Produto por peso teste"]');
assert.ok(catalog.contains(normal));assert.ok(weight.contains(weighted));assert.ok(!catalog.contains(weighted));
w.eval(fs.readFileSync('static/pro198.js','utf8'));d.dispatchEvent(new w.Event('DOMContentLoaded'));
function go(hash){w.history.replaceState(null,'',hash);w.dispatchEvent(new w.Event('hashchange'));}
for(const hash of ['#perfil','#configuracoes','#entrega-pagamento','#identidade','#exibicao-produtos','#horarios']){
 go(hash);assert.equal(profile.hidden,false,hash);assert.equal(catalog.hidden,true,hash);assert.equal(weight.hidden,true,hash);
}
go('#novo-produto');assert.equal(catalog.hidden,false);assert.equal(profile.hidden,true);assert.equal(weight.hidden,true);
go('#produtos-peso370');assert.equal(weight.hidden,false);assert.equal(catalog.hidden,true);assert.equal(d.getElementById('produtos-peso370').open,true);
go('#adicionais');assert.equal(d.getElementById('adicionais').hidden,false);assert.equal(catalog.hidden,true);assert.equal(weight.hidden,true);
w.close();console.log('Store settings, separate product forms, old links, and navigation verified');
