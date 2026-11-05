const {JSDOM}=require('jsdom'),fs=require('fs'),assert=require('node:assert/strict');
const dom=new JSDOM(`<details id="ingredientes320"><summary>Cadastro</summary><button data-import-ingredients357>Importar</button><form action="/painel/cardapio/ingredientes320"><input name="name"><input type="file" name="photo"></form><details><summary>Itens cadastrados</summary><details><summary>Bacon</summary></details><details><summary>Alface</summary></details></details></details><form data-meal-editor322><input type="file" name="photo"></form><div data-shared-picker155><label>Bacon</label><label>Queijo</label></div>`,{url:'https://nowup.test/painel',runScripts:'outside-only'});
const w=dom.window,d=w.document;w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};w.HTMLDialogElement.prototype.close=function(){this.open=false;};
const item={id:'01-01',name:'Pão brioche',category:'Pães',photo:'/galeria-nowup/ingredientes/01-01.jpg'};let posts=[];
w.fetch=async(url,opts={})=>{if(opts.method==='POST'){posts.push(opts.body);return {ok:true,url:'https://nowup.test/painel?ok=ingrediente#ingredientes320'};}if(url.endsWith('/itens-da-loja'))return {ok:true,json:async()=>[]};if(url===item.photo)return {ok:true,blob:async()=>new w.Blob(['photo'],{type:'image/jpeg'})};return {ok:true,json:async()=>[item]};};
w.eval(fs.readFileSync('static/ingredient-gallery357.js','utf8'));
const tick=()=>new Promise(r=>setImmediate(r));
(async()=>{
 assert.equal([...d.querySelectorAll('button')].filter(b=>b.textContent==='Enviar foto do aparelho').length,2);
 assert.equal([...d.querySelectorAll('button')].filter(b=>b.textContent==='Importar da galeria NowUp').length,2);
 d.querySelector('[data-import-ingredients357]').click();await tick();
 assert.equal(d.querySelectorAll('.nu357-card').length,1);
 const search=d.querySelector('.nu357-tools input');search.value='PAO';search.dispatchEvent(new w.Event('input'));assert.equal(d.querySelectorAll('.nu357-card').length,1);
 d.querySelector('.nu357-card button').click();
 const button=d.querySelector('.nu357-footer button');button.click();await tick();assert.equal(posts.length,0);assert.match(d.querySelector('.nu357-status').textContent,/Informe um preço/);
 const price=d.querySelector('.nu357-card input');price.value='3,50';price.dispatchEvent(new w.Event('input'));button.click();await tick();await tick();
 assert.equal(posts.length,1);assert.equal(posts[0].get('name'),'Pão brioche');assert.equal(posts[0].get('price'),'3,50');assert.equal(posts[0].get('photo').name,'nowup-01-01.jpg');assert.match(d.querySelector('.nu357-status').textContent,/1 item\(ns\) importado/);
 console.log('Gallery: both photo sources, accent-insensitive search, mandatory price and name/photo import verified.');
})().catch(e=>{console.error(e);process.exitCode=1;});
