const {JSDOM}=require('jsdom'),fs=require('fs'),assert=require('node:assert/strict');
const dom=new JSDOM('<script id="ingredient-catalog320" type="application/json">[]</script><div class="pro-dashboard"><form action="/painel/cardapio/produtos" data-meal-editor322="1"><input name="name" value="Meu lanche em edição"><input name="price" value="25,00"><select name="extras_mode"><option value="none">Nenhum</option></select><div data-editor192="" data-max192="3"></div><button type="submit">Salvar</button></form></div>',{url:'https://nowup.test/painel',runScripts:'outside-only'});
const w=dom.window,d=w.document,tick=()=>new Promise(r=>setImmediate(r));let registry=[{id:12,name:'Bacon salvo agora',image_filename:'bacon.jpg',price_cents:300}],requests=0;
w.fetch=async path=>{assert(path.endsWith('/itens-da-loja'));requests++;return {ok:true,json:async()=>registry.map(i=>({...i}))};};
for(const file of ['custom196.js','meal-groups324.js','compact200.js','ingredient-gallery357.js'])w.eval(fs.readFileSync('static/'+file,'utf8'));
(async()=>{
 const picker=[...d.querySelectorAll('details')].find(n=>n.querySelector('summary')?.textContent.includes('Galeria da minha loja'));assert(picker);picker.open=true;picker.dispatchEvent(new w.Event('toggle'));await tick();await tick();
 assert(d.querySelector('.nu325-list-item').textContent.includes('Bacon salvo agora'));d.querySelector('.nu325-list-item').click();const required=d.querySelector('[aria-label="Ingrediente obrigatório"]');required.checked=true;
 registry.push({id:13,name:'Tomate recém-importado',image_filename:'tomate.jpg',price_cents:100});const event=new w.Event('pageshow');Object.defineProperty(event,'persisted',{value:true});w.dispatchEvent(event);await tick();await tick();
 assert.equal(d.querySelectorAll('.nu325-list-item').length,2);assert.equal(required.checked,true);assert.equal(d.querySelector('[name=name]').value,'Meu lanche em edição');assert.equal(d.querySelectorAll('[aria-label=Ingrediente]').length,1);assert(requests>=2);
 console.log('Store gallery refreshes after opening and back-navigation; newly saved items appear without losing unsaved composition or mandatory flags.');
})().catch(e=>{console.error(e);process.exitCode=1;});
