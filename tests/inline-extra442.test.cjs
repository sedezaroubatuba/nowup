const {test}=require('node:test'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom'),fs=require('node:fs');
const flush=()=>new Promise(r=>setImmediate(r));
test('inline save preserves product draft, isolates validation and selects extra only in current product',async()=>{
 const form=id=>`<form id="${id}"><input name="name" value="Produto em edição"><label>Adicionais<select name="extras_mode"><option value="none">Sem adicionais</option><option value="selected">Selecionar</option></select></label><div data-shared-picker155><label><input type="checkbox" name="extra_ids" value="2" checked>Existente</label></div></form>`;
 const dom=new JSDOM(form('a')+form('b'),{url:'https://nowup.local',runScripts:'outside-only'}),w=dom.window;let posts=0;
 w.fetch=async(url,opts)=>{posts++;assert.equal(opts.body.get('price'),'4.50');assert.equal(opts.body.get('inline_paid442'),'1');return {ok:true,headers:{get:()=> 'application/json'},json:async()=>({id:9,name:'Queijo extra',price_cents:450,image_filename:''})};};
 w.eval(fs.readFileSync('static/inline-extra442.js','utf8'));
 const product=w.document.getElementById('a'),box=product.querySelector('.nu442-inline'),fields=box.querySelectorAll('input');
 assert.notEqual(fields[0].form,product);assert.equal(fields[0].required,true);assert.equal(fields[1].required,true);assert.equal(fields[2].required,false);
 fields[0].value='Queijo extra';fields[1].value='0';box.querySelector('button').click();await flush();assert.equal(posts,0);
 fields[1].value='4,50';box.querySelector('button').click();box.querySelector('button').click();await flush();
 assert.equal(posts,1);assert.equal(product.querySelector('[name=name]').value,'Produto em edição');assert.equal(product.querySelector('[name=extras_mode]').value,'selected');
 assert.equal(product.querySelector('[name=extra_ids][value="2"]').checked,true);assert.equal(product.querySelector('[name=extra_ids][value="9"]').checked,true);assert.equal(w.document.querySelector('#b [name=extra_ids][value="9"]').checked,false);
 assert.match(box.textContent,/Adicional salvo/);dom.window.close();
});
