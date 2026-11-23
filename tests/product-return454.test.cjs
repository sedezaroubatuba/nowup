const {test}=require('node:test');
const assert=require('node:assert/strict');
const {JSDOM}=require('jsdom');
const fs=require('node:fs');
const filters=fs.readFileSync('static/pro-panel-menu.js','utf8');
const returning=fs.readFileSync('static/pro-next138.js','utf8');
const key='nowup:catalog-return328';

function build(items,ok=''){
 const cards=items.map(([id,category,name],i)=>`
  <details id="produto-editor328-${id}" data-pro-product data-product-id="${id}"
    data-category="${category}" data-name="${name}">
   <summary tabindex="0">${name}</summary>
   <form action="/painel/cardapio/produtos/${id}" method="post">
     <label>Categoria<select name="category">
       <option value="Tabacaria" ${category==='Tabacaria'?'selected':''}>Tabacaria</option>
       <option value="Cervejas" ${category==='Cervejas'?'selected':''}>Cervejas</option>
     </select></label>
     <button type="submit">Salvar</button>
   </form>
   <form action="/painel/cardapio/produtos/${id}/excluir" method="post">
     <button type="submit">Excluir</button>
   </form>
  </details>`).join('');
 const html=`<div class="pro-dashboard">
   <section id="produtos-loja"><nav class="pro-product-filters">
    <button data-pro-category="all" class="active">Todos</button>
    <button data-pro-category="Tabacaria">Tabacaria</button>
    <button data-pro-category="Cervejas">Cervejas</button>
   </nav><input type="search" data-pro-search value=""></section>
   <div data-pro-products>${cards}</div>
 </div>`;
 const dom=new JSDOM(html,{url:'https://nowup.test/painel'+ok,runScripts:'outside-only',pretendToBeVisual:true});
 const w=dom.window;
 w.HTMLElement.prototype.scrollIntoView=function(){w.lastScroll454=this.id;};
 w.scrollTo=()=>{};
 return {dom,w};
}
const pause=(w,n=110)=>new Promise(resolve=>w.setTimeout(resolve,n));
function initialize(w){w.eval(filters);w.eval(returning);}
function choose(w,category){w.document.querySelector('[data-pro-category="'+category+'"]').click();}
function submit(w,id,dest){
 const editor=w.document.getElementById('produto-editor328-'+id);
 editor.querySelector('select[name=category]').value=dest;
 const form=editor.querySelector('form'),button=form.querySelector('button');
 form.dispatchEvent(new w.SubmitEvent('submit',{bubbles:true,cancelable:true,submitter:button}));
 return {state:JSON.parse(w.sessionStorage.getItem(key)),form};
}
async function returnPage(items,state,ok='?ok=produto#produtos-loja'){
 const result=build(items,ok);
 result.w.sessionStorage.setItem(key,JSON.stringify(state));
 initialize(result.w);
 await pause(result.w);
 return result;
}
test('category move preserves origin tab, hides moved item and opens the next product',async()=>{
 const first=build([[1,'Tabacaria','Seda 1'],[2,'Tabacaria','Seda 2'],[3,'Cervejas','Lata']]);
 initialize(first.w);await pause(first.w,35);choose(first.w,'Tabacaria');
 const {state,form}=submit(first.w,1,'Cervejas');
 assert.equal(state.category,'Tabacaria');
 assert.equal(state.previousCategory,'Tabacaria');
 assert.equal(state.newCategory,'Cervejas');
 assert.equal(state.next,'produto-editor328-2');
 assert.equal(new URL(form.action).searchParams.get('return_to328'),'produtos-loja');
 const second=await returnPage([[1,'Cervejas','Seda 1'],[2,'Tabacaria','Seda 2'],[3,'Cervejas','Lata']],state);
 const d=second.w.document;
 assert.equal(second.w.location.hash,'#produtos-loja');
 assert.equal(d.querySelector('[data-pro-category="Tabacaria"]').classList.contains('active'),true);
 assert.equal(d.getElementById('produto-editor328-1').hidden,true);
 assert.equal(d.getElementById('produto-editor328-2').hidden,false);
 assert.equal(d.getElementById('produto-editor328-2').open,true);
 assert.match(d.querySelector('.nu454-product-saved').textContent,/movido para Cervejas/);
 first.dom.window.close();second.dom.window.close();
});
test('ordinary price edit returns to the next product in the same category',async()=>{
 const first=build([[11,'Tabacaria','Seda A'],[12,'Tabacaria','Seda B']]);
 initialize(first.w);await pause(first.w,35);choose(first.w,'Tabacaria');
 const {state}=submit(first.w,11,'Tabacaria');
 const second=await returnPage([[11,'Tabacaria','Seda A'],[12,'Tabacaria','Seda B']],state);
 assert.equal(second.w.document.getElementById('produto-editor328-12').open,true);
 assert.equal(second.w.document.querySelector('[data-pro-category="Tabacaria"]').classList.contains('active'),true);
 first.dom.window.close();second.dom.window.close();
});
test('moving last item returns to previous visible item, not to the new category',async()=>{
 const first=build([[1,'Tabacaria','Seda A'],[2,'Tabacaria','Seda B']]);
 initialize(first.w);await pause(first.w,35);choose(first.w,'Tabacaria');
 const {state}=submit(first.w,2,'Cervejas');
 assert.equal(state.next,undefined);
 assert.equal(state.previous,'produto-editor328-1');
 const second=await returnPage([[1,'Tabacaria','Seda A'],[2,'Cervejas','Seda B']],state);
 assert.equal(second.w.document.getElementById('produto-editor328-1').open,true);
 assert.equal(second.w.document.getElementById('produto-editor328-2').hidden,true);
 first.dom.window.close();second.dom.window.close();
});
test('when moving the only item, stay in the now-empty source category',async()=>{
 const first=build([[1,'Tabacaria','Seda A']]);
 initialize(first.w);await pause(first.w,35);choose(first.w,'Tabacaria');
 const {state}=submit(first.w,1,'Cervejas');
 const second=await returnPage([[1,'Cervejas','Seda A']],state);
 const d=second.w.document;
 assert.equal(second.w.location.hash,'#produtos-loja');
 assert.equal(d.querySelector('[data-pro-category="Tabacaria"]').classList.contains('active'),true);
 assert.equal(d.getElementById('produto-editor328-1').hidden,true);
 assert.match(d.querySelector('.nu454-product-saved').textContent,/continua nesta categoria/);
 first.dom.window.close();second.dom.window.close();
});
test('global name search keeps underlying category when saved and cleared',async()=>{
 const first=build([[1,'Tabacaria','Seda'],[2,'Cervejas','Petra 350ml']]);
 initialize(first.w);await pause(first.w,35);choose(first.w,'Tabacaria');
 const search=first.w.document.querySelector('[data-pro-search]');search.value='Petra';search.dispatchEvent(new first.w.Event('input',{bubbles:true}));
 const {state}=submit(first.w,2,'Cervejas');
 assert.equal(state.category,'Tabacaria');
 assert.equal(state.searches[0],'Petra');
 const second=await returnPage([[1,'Tabacaria','Seda'],[2,'Cervejas','Petra 350ml']],state);
 const d=second.w.document;
 assert.equal(d.querySelector('[data-pro-search]').value,'Petra');
 assert.equal(d.querySelector('[data-pro-category="all"]').classList.contains('active'),true);
 assert.equal(second.w.NOWUP_PRO_PRODUCT_FILTERS.current(),'Tabacaria');
 d.querySelector('[data-pro-search]').value='';
 d.querySelector('[data-pro-search]').dispatchEvent(new second.w.Event('input',{bubbles:true}));
 assert.equal(d.querySelector('[data-pro-category="Tabacaria"]').classList.contains('active'),true);
 first.dom.window.close();second.dom.window.close();
});

test('confirmed deletion keeps the source category and continues to the next item',async()=>{
 const first=build([[1,'Tabacaria','Seda A'],[2,'Tabacaria','Seda B'],[3,'Cervejas','Skol']]);
 initialize(first.w);await pause(first.w,35);choose(first.w,'Tabacaria');
 const deleted=first.w.document.getElementById('produto-editor328-1').querySelector('form[action$="/excluir"]');
 deleted.dispatchEvent(new first.w.SubmitEvent('submit',{bubbles:true,cancelable:true,submitter:deleted.querySelector('button')}));
 const state=JSON.parse(first.w.sessionStorage.getItem(key));
 assert.equal(state.deleted,true);
 assert.equal(state.next,'produto-editor328-2');
 const second=await returnPage([[2,'Tabacaria','Seda B'],[3,'Cervejas','Skol']],state,'?ok=produto-excluido#cardapio');
 assert.equal(second.w.location.hash,'#produtos-loja');
 assert.equal(second.w.document.querySelector('[data-pro-category="Tabacaria"]').classList.contains('active'),true);
 assert.equal(second.w.document.getElementById('produto-editor328-2').open,true);
 assert.match(second.w.document.querySelector('.nu454-product-saved').textContent,/Produto excluído/);
 first.dom.window.close();second.dom.window.close();
});
