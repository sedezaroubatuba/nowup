const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {JSDOM}=require('jsdom');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function setup(html){const dom=new JSDOM(html,{url:'https://nowup.test/painel',runScripts:'outside-only'});const w=dom.window;w.HTMLDialogElement.prototype.showModal=function(){this.open=true};w.HTMLDialogElement.prototype.close=function(){this.open=false};w.eval(fs.readFileSync('static/nowup-dialogs.js','utf8'));return w;}
const click=(w,selector)=>w.document.querySelector(selector).click();
test('recusa exige motivo, preserva submitter e envia uma única vez',async()=>{
 const w=setup('<div class="pro-dashboard"><form data-cancel-form><input name="reason"><button name="status" value="rejected">Recusar</button></form></div>');
 await tick();w.requestAnimationFrame=()=>0;w.eval(fs.readFileSync('static/pro-panel-menu.js','utf8'));const f=w.document.querySelector('form'),b=f.querySelector('button');let submits=[];f.addEventListener('submit',e=>{e.preventDefault();if(f.elements.reason.value)submits.push({reason:f.elements.reason.value,submitter:e.submitter})});
 f.requestSubmit(b);await tick();click(w,'.nu-dialog-actions button:last-child');assert.equal(submits.length,0);const input=w.document.querySelector('textarea');input.value='Produto indisponível';input.dispatchEvent(new w.Event('input'));click(w,'.nu-dialog-actions button:last-child');await tick();assert.deepEqual(submits,[{reason:'Produto indisponível',submitter:b}]);assert.equal(w.document.querySelector('dialog'),null);w.close();
});
test('cancelar exclusão não envia; confirmar preserva botão e validação',async()=>{
 const w=setup('<form action="/painel/item/excluir"><input name="id" value="7"><button name="operation" value="delete">Excluir</button></form>');const f=w.document.querySelector('form'),b=f.querySelector('button');let sent=0;f.addEventListener('submit',e=>{e.preventDefault();sent++;assert.equal(e.submitter,b)});
 f.requestSubmit(b);await tick();click(w,'.nu-dialog-secondary');await tick();assert.equal(sent,0);f.requestSubmit(b);await tick();click(w,'.nu-dialog-actions button:last-child');await tick();assert.equal(sent,1);w.close();
});
test('seleção pesquisável preserva opções, eventos e valor do formulário',async()=>{
 const w=setup('<form><label>Categoria<select name="category">'+['Todas','Pães','Carnes','Frango','Queijos','Vegetais','Molhos','Extras','Acompanhamentos'].map(x=>`<option>${x}</option>`).join('')+'<option disabled>Indisponível</option></select></label></form>');const s=w.document.querySelector('select');let changes=0;s.addEventListener('change',()=>changes++);s.click();await tick();assert.equal(w.document.querySelector('h2').textContent,'Categoria');const search=w.document.querySelector('input');search.value='paes';search.dispatchEvent(new w.Event('input'));const visible=[...w.document.querySelectorAll('.nu-dialog-option')].filter(b=>!b.hidden);assert.equal(visible.length,1);visible[0].click();await tick();assert.equal(s.value,'Pães');assert.equal(changes,1);assert.equal(new w.FormData(s.form).get('category'),'Pães');s.click();await tick();w.document.querySelector('dialog').dispatchEvent(new w.Event('cancel',{cancelable:true}));await tick();assert.equal(s.value,'Pães');assert.equal(changes,1);w.close();
});
test('saída pede confirmação mesmo sem formaction no botão',async()=>{
 const w=setup('<form action="/sair" method="post"><button>Sair</button></form>');let sent=0;w.document.querySelector('form').addEventListener('submit',e=>{e.preventDefault();sent++});w.document.querySelector('button').click();await tick();assert.match(w.document.querySelector('dialog').textContent,/sair da sua conta/);click(w,'.nu-dialog-secondary');await tick();assert.equal(sent,0);w.close();
});
