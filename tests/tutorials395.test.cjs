const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const {JSDOM}=require('jsdom');
function fixture(fashion=false){
 const dom=new JSDOM(`<body class="professional-area"><div class="pro-dashboard"><main>
 <section id="inicio"><a class="nu221-store-link" href="/p/demo">Ver minha loja</a></section>
 <section id="tutoriais395" data-fashion="${fashion?'1':'0'}"><input data-tutorial-search395><details data-layout-examples395><summary>Exemplos</summary></details><div data-tutorial-list395></div><p data-tutorial-empty395 hidden></p></section>
 <section id="perfil"><input name="display_name" value="Loja real"><input name="whatsapp" value="12999999999"><details><summary>Exibição</summary><section id="exibicao-produtos"><form><input name="carousel_layout235" value="large" type="radio"><input name="carousel_layout235" value="pair" type="radio"><input name="carousel_layout235" value="compact" type="radio" checked></form></section></details></section>
 <section id="adicionais"><details id="ingredientes320"><summary>Ingredientes</summary><form><input name="name" value="Bacon"><input name="price" value="5,00" required aria-describedby="price-help"><button>Salvar</button></form><button data-import-ingredients357>Importar</button></details></section>
 <section id="lanches-refeicoes322"><details id="novo-lanche322"><summary>Novo lanche</summary><input name="name"><div data-editor192></div><select name="extras_mode"></select></details></section>
 </main></div></body>`,{url:'https://nowup.example/painel#tutoriais395',runScripts:'outside-only',pretendToBeVisual:true});
 const w=dom.window,d=w.document;let frames=[];w.requestAnimationFrame=fn=>{frames.push(fn);return frames.length;};w.cancelAnimationFrame=()=>{};
 w.HTMLElement.prototype.scrollIntoView=function(){};w.HTMLElement.prototype.getClientRects=function(){return [{width:300,height:40}];};
 for(const file of ['static/pro198.js','static/tutorials-data395.js','static/tutorials395.js'])w.eval(fs.readFileSync(file,'utf8'));
 d.dispatchEvent(new w.Event('DOMContentLoaded'));return {dom,w,d,flush:()=>{const f=frames;frames=[];f.forEach(fn=>fn());}};
}
function start(f,name){const card=[...f.d.querySelectorAll('.nu395-topic')].find(c=>c.querySelector('h3').textContent===name);assert.ok(card,name);card.querySelector('button').click();f.flush();}
function next(f){f.d.querySelector('.nu395-guide button.primary').click();f.flush();}
test('guide navigates actual sections, opens details and preserves form values and accessibility',()=>{
 const f=fixture();let submits=0;f.d.addEventListener('submit',()=>submits++);
 start(f,'Ingredientes e adicionais');assert.equal(f.w.location.hash,'#ingredientes320');assert.equal(f.d.querySelector('#adicionais').hidden,false);assert.equal(f.d.querySelector('#ingredientes320').open,true);
 next(f);const price=f.d.querySelector('#ingredientes320 [name=price]');assert.ok(price.classList.contains('nu395-highlight'));assert.equal(price.value,'5,00');assert.equal(price.getAttribute('aria-describedby'),'price-help nu395-step-copy');
 f.d.dispatchEvent(new f.w.KeyboardEvent('keydown',{key:'Escape'}));assert.equal(price.getAttribute('aria-describedby'),'price-help');assert.equal(f.d.querySelector('.nu395-guide').hidden,true);assert.equal(submits,0);f.dom.window.close();
});
test('layout guide never changes or saves the selected layout and finishes back in tutorials',()=>{
 const f=fixture();start(f,'Vitrine: 1, 2 ou 4 produtos');next(f);assert.equal(f.w.location.hash,'#exibicao-produtos');assert.ok(f.d.querySelector('#exibicao-produtos [value=large]').classList.contains('nu395-highlight'));assert.equal(f.d.querySelector('#exibicao-produtos [value=compact]').checked,true);
 for(let i=0;i<4;i++)next(f);assert.equal(f.w.location.hash,'#tutoriais395');assert.equal(f.d.querySelector('.nu395-guide').hidden,true);f.dom.window.close();
});
test('missing plan-dependent target shows an explanation without throwing',()=>{
 const f=fixture();start(f,'Pix e pagamentos');assert.match(f.d.querySelector('.nu395-guide [role=status]').textContent,/não está disponível/);assert.equal(f.d.querySelector('.nu395-guide').hidden,false);f.dom.window.close();
});
test('search finds payments and fashion does not teach food or carousel settings',()=>{
 const f=fixture(true);const names=[...f.d.querySelectorAll('.nu395-topic h3')].map(n=>n.textContent);assert.ok(names.includes('Catálogo de moda'));assert.ok(!names.includes('Montar um lanche'));assert.ok(!names.includes('Vitrine: 1, 2 ou 4 produtos'));
 const input=f.d.querySelector('[data-tutorial-search395]');input.value='pix';input.dispatchEvent(new f.w.Event('input'));assert.ok(f.d.querySelector('.nu395-topic').textContent.includes('Pix'));f.dom.window.close();
});
test('browser navigation and closing tutorial leave merchant edits intact',()=>{
 const f=fixture();start(f,'Primeiros passos');next(f);const name=f.d.querySelector('[name=display_name]');name.value='Loja editada';f.w.dispatchEvent(new f.w.PopStateEvent('popstate'));assert.equal(f.d.querySelector('.nu395-guide').hidden,true);assert.equal(name.value,'Loja editada');f.dom.window.close();
});
