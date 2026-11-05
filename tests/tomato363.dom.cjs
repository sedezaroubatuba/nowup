const {JSDOM}=require('jsdom'),fs=require('fs'),assert=require('node:assert/strict');
const tick=()=>new Promise(r=>setImmediate(r));
async function scenario(inline,photo,price){
 const dom=new JSDOM('<button data-import-ingredients357>Importar</button><script id="ingredient-catalog320" type="application/json">[]</script>',{url:'https://nowup.test/painel',runScripts:'outside-only'}),w=dom.window,d=w.document;
 w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};w.HTMLDialogElement.prototype.close=function(){this.open=false;};
 let own={id:3,name:'Tomate',image_filename:photo,price_cents:price},posts=[],attached=[],photoRequests=0;
 w.fetch=async(url,opts={})=>{if(opts.method==='POST'){posts.push(opts.body);assert.equal(opts.body.get('ingredient_id'),'3','update existing tomato instead of duplicate POST');own={...own,price_cents:Number(opts.body.get('price').replace(',','.'))*100,image_filename:opts.body.get('photo')?'new-gallery.jpg':own.image_filename};return {ok:true,url:'https://nowup.test/painel?ok=ingrediente'};}if(url.endsWith('/itens-da-loja'))return {ok:true,json:async()=>[{...own}]};if(url.endsWith('.jpg')){photoRequests++;return {ok:true,blob:async()=>new w.Blob(['photo'],{type:'image/jpeg'})};}return {ok:true,json:async()=>[{id:'06-04',name:'Tomate',category:'Vegetais',photo:'/tomate.jpg'}]};};
 w.eval(fs.readFileSync('static/ingredient-gallery357.js','utf8'));
 const button=d.querySelector('button');if(inline)w.NOWUP_GALLERY357.addIngredients(button,items=>attached=items);else button.click();await tick();await tick();d.querySelector('.nu357-card button').click();
 const field=d.querySelector('.nu357-card input');assert.equal(field.readOnly,price!=null);
 if(price==null){assert.equal(field.value,'','missing price must not silently become zero');d.querySelector('.nu357-footer button').click();await tick();assert.equal(posts.length,0);field.value='1,50';field.dispatchEvent(new w.Event('input'));}
 d.querySelector('.nu357-footer button').click();for(let i=0;i<6;i++)await tick();
 if(!photo||price==null){assert.equal(posts.length,1);assert.equal(posts[0].get('photo')!=null,!photo);assert.equal(photoRequests,photo?0:1);assert.equal(own.price_cents,price??150);assert.equal(own.image_filename,photo||'new-gallery.jpg');}else assert.equal(posts.length,0);
 if(inline){assert.equal(attached.length,1);assert.equal(attached[0].id,3);assert.equal(attached[0].price_cents,own.price_cents);assert.equal(d.querySelector('dialog').open,false);}else assert.equal(d.querySelector('.nu357-footer button:last-child').hidden,false,'finish available when reusing registered item');
}
(async()=>{for(const inline of [false,true])for(const [photo,price] of [['old-tomato.jpg',null],['',250],['old-tomato.jpg',250]])await scenario(inline,photo,price);console.log('Legacy tomato: fill missing price, preserve existing photo/price, complete missing photo, reuse without duplication in registration and meal composer.');})().catch(e=>{console.error(e);process.exitCode=1;});
