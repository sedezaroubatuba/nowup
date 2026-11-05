const {JSDOM}=require('jsdom'),fs=require('fs'),assert=require('node:assert/strict');
const item={id:71,name:'Bacon em fatias',image_filename:'bacon-photo.jpg',price_cents:350};
const form=()=>'<form action="/painel/cardapio/produtos" data-meal-editor322="1"><input name="name" value="Lanche"><input name="price" value="25,00"><input name="photo" type="file"><select name="extras_mode"><option value="none">Sem adicionais</option></select><div data-editor192="" data-max192="3"></div><button type="submit">Salvar</button></form>';
const dom=new JSDOM('<script id="ingredient-catalog320" type="application/json">'+JSON.stringify([item])+'</script><div class="pro-dashboard">'+form()+form()+'</div>',{url:'https://nowup.test/painel',runScripts:'outside-only'}),w=dom.window,d=w.document;
w.eval(fs.readFileSync('static/custom196.js','utf8'));w.eval(fs.readFileSync('static/meal-groups324.js','utf8'));w.eval(fs.readFileSync('static/compact200.js','utf8'));w.eval(fs.readFileSync('static/ingredient-gallery357.js','utf8'));
assert.equal(d.querySelectorAll('[data-compose-gallery358]').length,0);assert.equal(d.querySelectorAll('[data-gallery-result358]').length,0);
assert.equal([...d.querySelectorAll('button')].filter(b=>b.textContent==='Importar da galeria NowUp').length,0,'main product photos must not offer ingredient library');
for(const [n,f] of [...d.querySelectorAll('form')].entries()){
 const search=f.querySelector('[aria-label="Buscar ingrediente cadastrado na loja"]');assert(search);search.value='bacon';search.dispatchEvent(new w.Event('input'));
 const result=f.querySelector('.nu325-list-item');assert(result);result.click();
 const row=[...f.querySelectorAll('.nu192-row')].find(r=>r.querySelector('[aria-label=Ingrediente]')?.value===item.name);assert(row);assert.equal(row.querySelector('img').getAttribute('src'),'/uploads/bacon-photo.jpg');assert.equal(row.closest('details').open,true);
 result.click();assert.equal(f.querySelectorAll('[aria-label=Ingrediente]').length,1,'same ingredient cannot duplicate within one meal');
 row.querySelector('[aria-label="Ingrediente obrigatório"]').checked=n===0;
 f.dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));const config=JSON.parse(f.querySelector('[name=customization192]').value);assert.equal(config.ingredients[0].ingredient_id320,71);assert.equal(config.ingredients[0].removable,n!==0);assert.equal(config.ingredients[0].image_filename,item.image_filename);assert.equal(f.querySelector('[name=photo]').files.length,0);
}
assert.equal(item.price_cents,350);console.log('Store-only composition: reuse saved ingredient/photo in two meals, per-meal mandatory flag, no duplicate, no gallery import in composer.');
