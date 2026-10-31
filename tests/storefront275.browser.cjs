const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const {chromium}=require('playwright');
const css=['static/products231.css','static/storefront232.css','static/offers256.css'].map(f=>fs.readFileSync(f,'utf8')).join('\n');
const code=fs.readFileSync('static/storefront187.js','utf8');
const cards=[...Array(6)].map((_,i)=>({id:i+1,name:'Combo '+i,category:'cervejas',combo:'1',price:2000,regular:2000})).concat([{id:7,name:'Cerveja promoção',category:'cervejas',combo:'0',price:400,regular:500}]);
const fixture=`<!doctype html><style>*{box-sizing:border-box}body{margin:0}.nu190-track{display:flex;overflow:auto}.nu190-page{flex:0 0 100%}[hidden]{display:none!important}${css}</style><body class="public-profile-area nu233-store nu232-store"><template id="nu187-store-template"><section class="nu187-intro"><h1>Loja</h1></section></template><main data-native-menu data-carousel-layout="compact"><div class="nu-menu-sticky"><div class="nu83-catalog-heading"><input data-product-search></div><nav class="menu-category-nav"><button data-category-filter="all">Todos</button><button data-category-filter="cervejas">Cervejas</button></nav></div><div class="menu-layout"><div class="menu-products">${cards.map(c=>`<article data-product data-id="${c.id}" data-name="${c.name}" data-category="${c.category}" data-combo256="${c.combo}" data-available256="1" data-price="${c.price}" data-regular256="${c.regular}" data-max="99"><div class="menu-product-info"><small>Cervejas</small><p>Descrição</p><input data-product-quantity value="1"><button data-add>Adicionar</button></div></article>`).join('')}</div></div></main><script>window.NowUpCategory230={create:()=>document.createElement('span')};</script><script>${code}</script>`;
test('large sideways combo showcase, four-card view and no combo duplication in regular category',async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.NOWUP_CHROME_EXECUTABLE||undefined,args:['--no-sandbox']});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844}}),errors=[];page.on('pageerror',e=>errors.push(e.message));await page.setContent(fixture);await page.waitForSelector('.nu275-combo-section');
  assert.equal(await page.locator('[data-category190="cervejas"] .nu190-card').count(),1);
  const size=await page.locator('.nu275-combo-section .nu190-page').first().evaluate(e=>({width:e.getBoundingClientRect().width,parent:e.parentElement.clientWidth}));assert.ok(size.width>size.parent*.75&&size.width<size.parent*.9);
  await page.locator('.nu275-combo-section header button').click();assert.equal(await page.locator('.nu275-combos-grid .nu190-card').count(),6);
  const grid=await page.locator('.nu275-combos-grid').evaluate(e=>({cols:getComputedStyle(e).gridTemplateColumns.split(' ').length,height:e.firstElementChild.getBoundingClientRect().height}));assert.equal(grid.cols,2);assert.ok(grid.height<300);
  await page.locator('[data-category-filter="cervejas"]').click();assert.ok(await page.locator('.nu275-combos-grid').isHidden());assert.deepEqual(errors,[]);
 }finally{await browser.close();}
});
