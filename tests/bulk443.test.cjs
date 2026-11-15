const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),{JSDOM}=require('jsdom');
const run=(w,path)=>w.eval(fs.readFileSync(path,'utf8'));
const click=(d,text)=>{const b=[...d.querySelectorAll('button')].find(b=>b.textContent.startsWith(text));assert.ok(b,text);b.click();};
test('combo adds five search matches together, retains query and existing choice, no duplicates',()=>{
 const products=[{id:1,name:'Gelo tradicional',available:true},...Array.from({length:5},(_,i)=>({id:i+2,name:'Gelo de coco '+i,available:true})),{id:8,name:'Gelo de coco indisponivel',available:false}];
 const dom=new JSDOM('<form><input name="price" value="100"><div id="editor"></div></form><script id="combo-catalog298" type="application/json">'+JSON.stringify(products)+'</script>',{runScripts:'outside-only'}),w=dom.window,d=w.document;
 run(w,'static/combo-editor301.js');w.NOWUP_COMBO301(d.querySelector('#editor'),d.querySelector('form'),{combo_items:[{product_id:1,name:'Gelos',quantity:4}]});
 const search=d.querySelector('input[type=search]');search.value='gelo de coco';search.dispatchEvent(new w.Event('input'));click(d,'Marcar todos os resultados (5)');click(d,'Adicionar marcados (5)');
 assert.equal(d.querySelectorAll('.nu301-selected-product').length,6);assert.equal(search.value,'gelo de coco');d.querySelector('form').dispatchEvent(new w.Event('submit',{cancelable:true}));
 const cfg=JSON.parse(d.querySelector('[name=customization192]').value);assert.equal(cfg.groups[0].product_ids.length,6);assert.equal(cfg.groups[0].max,4);assert.equal(new Set(cfg.groups[0].product_ids).size,6);dom.window.close();
});
test('extras select only matching results, preserve unrelated selection, and clear filtered results',()=>{
 const dom=new JSDOM('<form><input name="name" value="Rascunho"><select name="extras_mode"><option value="selected">Selecionar</option></select><div data-shared-picker155><label><input name="extra_ids" type="checkbox" value="1" checked>Bacon</label><label><input name="extra_ids" type="checkbox" value="2">Queijo mussarela</label><label><input name="extra_ids" type="checkbox" value="3">Queijo cheddar</label></div></form>',{runScripts:'outside-only'}),w=dom.window,d=w.document;
 run(w,'static/bulk-extras443.js');const search=d.querySelector('input[type=search]');search.value='queijo';search.dispatchEvent(new w.Event('input'));click(d,'Selecionar todos os resultados (2)');assert.equal(d.querySelectorAll('[name=extra_ids]:checked').length,3);click(d,'Desmarcar resultados');assert.equal(d.querySelectorAll('[name=extra_ids]:checked').length,1);assert.equal(d.querySelector('[name=name]').value,'Rascunho');dom.window.close();
});
