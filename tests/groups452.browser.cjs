const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {chromium}=require('playwright');
const file=name=>fs.readFileSync(path.join(__dirname,'..',name),'utf8');
const css=[file('static/catalog162.css'),file('static/groups260.css'),file('static/groups452.css')].join('\n');
const repeat=(n)=>Array.from({length:n},(_,i)=>{
  const id=i+1;const name=['Banana tropical','Hapocalyx mint','Citrus ice','Melancia fresh','Morango','Uva','Menta'][i%7];
  return '<article class="nu-group260-row" data-product data-id="'+id+'" data-name="'+name+'">'
    +'<img alt="" width="58" height="66" src="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%2258%22 height=%2266%22/%3E">'
    +'<div class="nu-group260-row-main"><h4>'+name+'</h4><strong>R$ 17,00</strong></div>'
    +'<div class="product-buy"><label>Qtd. <button type="button">−</button><input data-product-quantity type="number" value="1"><button type="button">+</button></label>'
    +'<button type="button" data-add>Adicionar</button></div></article>';
}).join('');
const html='<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
  +'<style>'+css+'</style></head><body class="public-profile-area">'
  +'<main class="native-menu" data-native-menu><div class="menu-products">'
  +'<details class="menu-product nu-group260" data-product data-group260="1" data-id="99" open>'
  +'<summary class="nu-group260-cover"><img alt="" width="92" height="94" src="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%2292%22 height=%2294%22/%3E">'
  +'<div class="menu-product-info"><h3>Essências Ziggy</h3><p>Linha completa de essências com diversos sabores para escolher.</p>'
  +'<b class="nu-group260-open">Escolher entre 7 opções</b></div></summary>'
  +'<div class="nu-group260-items"><h3 class="nu452-list-title">Opções de Essências Ziggy</h3>'
  +'<p class="nu-group260-hint">Escolha o sabor e adicione ao carrinho.</p>'+repeat(7)+'</div></details>'
  +'<article class="menu-product" data-product data-id="89"><div class="menu-product-info"><h3>Produto comum</h3></div></article>'
  +'</div></main></body></html>';
async function runWithWidth(width){
 const browser=await chromium.launch({headless:true,...(process.env.NOWUP_CHROME_EXECUTABLE?{executablePath:process.env.NOWUP_CHROME_EXECUTABLE}:{})});
 const page=await browser.newPage({viewport:{width,height:850},deviceScaleFactor:1});
 await page.setContent(html);await page.addScriptTag({content:file('static/groups452.js')});
 return {browser,page};
}
for(const width of [360,390,768]){
 test('grouped product accordion preview 2 aligns rows at '+width+'px',async()=>{
  const {browser,page}=await runWithWidth(width);
  try{
   const group=page.locator('.nu-group260'),rows=page.locator('.nu-group260-row'),show=page.locator('.nu452-show-more');
   assert.equal(await group.evaluate(el=>getComputedStyle(el).display),'block','group must not be a two-column product grid');
   assert.equal(await rows.count(),7);
   assert.equal(await rows.filter({visible:true}).count(),4,'only four initial flavors');
   assert.equal(await show.isVisible(),true);
   assert.match(await show.textContent(),/Ver todas as 7 opções/);
   const cover=await page.locator('.nu-group260-cover').boundingBox();
   const title=page.locator('.nu-group260-cover h3'),titleRect=await title.boundingBox();
   assert.ok(titleRect.width>=80,'parent title must have readable width');
   assert.ok(titleRect.height<75,'parent title must not become vertical letters');
   assert.ok(cover.width<=width && cover.x>=0);
   for(let i=0;i<4;i++){
    const row=rows.nth(i);
    const bounds=await row.boundingBox();
    const img=await row.locator('img').boundingBox();
    const name=await row.locator('h4').boundingBox();
    const buy=await row.locator('.product-buy').boundingBox();
    const button=await row.locator('[data-add]').boundingBox();
    assert.ok(bounds.x>=0 && bounds.x+bounds.width<=width+1,'row fits viewport '+JSON.stringify(bounds));
    assert.ok(img.x+img.width<=name.x+1,'photo before text');
    assert.ok(name.width>=38 && name.height<94,'no vertical letter columns: '+JSON.stringify(name));
    assert.ok(name.x+name.width<=buy.x+2,'name and add controls do not overlap');
    assert.ok(button.width>=80,'Add label is legible');
    assert.ok(button.x>=buy.x-1 && button.x+button.width<=width+1);
   }
   await show.click();assert.equal(await rows.filter({visible:true}).count(),7);
   assert.match(await show.textContent(),/Ver menos/);
   await show.click();assert.equal(await rows.filter({visible:true}).count(),4);
   await page.locator('.nu-group260 > summary').click();
   assert.equal(await group.getAttribute('open'),null);
   await page.locator('.nu-group260 > summary').click();
   assert.equal(await rows.filter({visible:true}).count(),4);
   // Plain products still retain their own established card rules.
   assert.equal(await page.locator('.menu-products > article.menu-product').evaluate(el=>getComputedStyle(el).display),'grid');
  }finally{await browser.close();}
 });
}
