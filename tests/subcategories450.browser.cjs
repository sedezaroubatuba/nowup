const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {chromium}=require('playwright');
const folder=path.resolve(__dirname,'..');
const read=name=>fs.readFileSync(path.join(folder,name),'utf8');
const css=[read('static/pro198.css'),read('static/subcategories261.css'),read('static/subcategories449.css')].join('\n');
const js=read('static/pro-panel-menu.js');
const fixture='<html><head><meta name="viewport" content="width=device-width,initial-scale=1"></head>'
+'<body class="professional-area"><main class="pro-dashboard">'
+'<details id="categorias-loja" class="nu449-category-manager" open><div class="category-admin-list nu449-category-list"><div class="category-admin-row nu449-category-row">'
+'<details class="nu449-category-card" open><summary class="nu449-category-summary"><strong class="nu449-category-name">Tabacaria</strong></summary>'
+'<div class="nu449-category-body"><div class="nu449-subcategory-section"><details class="nu449-new-subcategory">'
+'<summary class="nu449-add-button">＋ Adicionar subcategoria</summary>'
+'<form class="nu449-subcategory-form"><input type="hidden" name="category_id" value="7">'
+'<label>Nome da subcategoria<input class="input" name="name" placeholder="Ex.: Sedas, Tabacos, Piteiras" required></label>'
+'<button type="submit" class="btn primary">Salvar subcategoria</button></form>'
+'</details></div></div></details></div></div></details>'
+'<div id="produtos-loja"><input type="search" data-pro-search placeholder="Pesquisar produto">'
+'<nav class="pro-product-filters"><button type="button" data-pro-category="all" class="active">Todos</button>'
+'<button type="button" data-pro-category="Tabacaria">Tabacaria</button>'
+'<button type="button" data-pro-category="Bebidas">Bebidas</button></nav>'
+'<div class="product-admin-grid" data-pro-products>'
+'<details data-pro-product data-name="Seda RAW" data-product-id="12" data-category="Tabacaria" data-featured="0"><summary><b>Seda RAW</b></summary></details>'
+'<details data-pro-product data-name="Heineken Long Neck" data-product-id="17" data-category="Bebidas" data-featured="0"><summary><b>Heineken Long Neck</b></summary></details>'
+'</div></div></main></body></html>';
async function launch(width=390){
 const browser=await chromium.launch({headless:true,...(process.env.NOWUP_CHROME_EXECUTABLE?{executablePath:process.env.NOWUP_CHROME_EXECUTABLE}:{})});
 const page=await browser.newPage({viewport:{width,height:844}});
 await page.setContent(fixture);
 await page.addStyleTag({content:css});
 await page.addScriptTag({content:js});
 return {browser,page};
}
test('closed form stays hidden; open form has non-overlapping input and save button on mobile',async()=>{
 const {browser,page}=await launch();
 try{
  const form=page.locator('.nu449-subcategory-form');
  const summary=page.locator('.nu449-new-subcategory > summary');
  const input=page.locator('.nu449-subcategory-form input[name=name]');
  const button=page.locator('.nu449-subcategory-form button');
  assert.equal(await form.isVisible(),false,'Salvar subcategoria must not appear before opening the form');
  await summary.click();
  assert.equal(await input.isVisible(),true);
  assert.equal(await button.isVisible(),true);
  const top=await summary.boundingBox(),field=await input.boundingBox(),save=await button.boundingBox();
  assert.ok(field.y>=top.y+top.height+2,'Name input must be below the add button');
  assert.ok(save.y>=field.y+field.height+5,'Save button must be below the name input, never overlapping');
  assert.ok(field.x>=0 && field.x+field.width<=390 && save.x>=0 && save.x+save.width<=390,'form must fit the viewport');
  await summary.click();
  assert.equal(await form.isVisible(),false,'closing the section hides the form again');
 }finally{await browser.close();}
});
test('merchant product search works across categories even after choosing one',async()=>{
 const {browser,page}=await launch();
 try{
  const search=page.locator('[data-pro-search]');
  const tabacaria=page.locator('[data-pro-category=Tabacaria]');
  const soda=page.locator('[data-pro-product][data-product-id="12"]');
  const beer=page.locator('[data-pro-product][data-product-id="17"]');
  await tabacaria.click();
  assert.equal(await soda.isVisible(),true);
  assert.equal(await beer.isVisible(),false);
  await search.fill('heineken');
  assert.equal(await soda.isVisible(),false);
  assert.equal(await beer.isVisible(),true,'search must find products even outside the selected category');
  assert.equal(await page.locator('[data-pro-category=all]').getAttribute('aria-pressed'),'true');
  await search.fill('RAW');
  assert.equal(await soda.isVisible(),true);
  assert.equal(await beer.isVisible(),false);
  await search.fill('');
  assert.equal(await soda.isVisible(),true,'clearing search restores previously selected category');
  assert.equal(await beer.isVisible(),false);
  await page.locator('[data-pro-category=Bebidas]').click();
  assert.equal(await soda.isVisible(),false);
  assert.equal(await beer.isVisible(),true);
 }finally{await browser.close();}
});
test('public catalog search cannot keep stale category filter after typing',()=>{
 const native=read('static/menu88.js');
 const storefront=read('static/storefront187.js');
 assert.ok(native.includes("category='all'"));
 assert.ok(storefront.includes("showProducts();"));
 assert.ok(storefront.includes("search.dispatchEvent(new Event('input'"));
});
