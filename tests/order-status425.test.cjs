const {test}=require('node:test'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom'),fs=require('node:fs');
const tick=()=>new Promise(r=>setImmediate(r));
test('status changes inside receipt once and preserves conversation',async()=>{
 const block='<section data-order-status425><form data-status-form425 method="post" action="/painel/pedidos/1/status"><button name="status" value="preparing">Em preparo</button></form><p data-feedback425></p></section>';
 const dom=new JSDOM(block+'<article class="nu401-paper">Confirmado</article><textarea>Conversa pendente</textarea>',{url:'https://nowup.test/pedido/token',runScripts:'outside-only'}),w=dom.window;let posts=0,legacy=0;
 w.document.addEventListener('submit',()=>legacy++);
 w.fetch=async(url,options={})=>{if(options.method==='POST'){posts++;assert.equal(options.body.get('status'),'preparing');return {ok:true,json:async()=>({id:1,status:'preparing'})};}return {ok:true,text:async()=>block+'<article class="nu401-paper">Em preparo</article>'};};
 try{w.eval(fs.readFileSync('static/order-status425.js','utf8'));const form=w.document.querySelector('form'),button=form.querySelector('button');for(let i=0;i<2;i++)form.dispatchEvent(new w.SubmitEvent('submit',{bubbles:true,cancelable:true,submitter:button}));for(let i=0;i<6;i++)await tick();assert.equal(posts,1);assert.equal(legacy,0);assert.equal(w.document.querySelector('.nu401-paper').textContent,'Em preparo');assert.equal(w.document.querySelector('textarea').value,'Conversa pendente');assert.equal(w.location.pathname,'/pedido/token');assert.match(w.document.querySelector('[data-feedback425]').textContent,/atualizado/);}finally{w.close();}
});
