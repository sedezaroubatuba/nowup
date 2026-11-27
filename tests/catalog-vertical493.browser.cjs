const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const {chromium}=require('playwright');
test('mobile shelf has four products, green counter and no horizontal arrows',async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.NOWUP_CHROME_EXECUTABLE||undefined,args:['--no-sandbox']});
 try{
 const page=await browser.newPage({viewport:{width:390,height:844}});
 const css=['storefront187','showcase190','category191','products201','products231','storefront232','offers256','original281','catalog-layout371','catalog-vertical493'].map(f=>fs.readFileSync('static/'+f+'.css','utf8')).join('\n');
 const cards=Array.from({length:5},(_,i)=>`<article class="menu-product" data-product data-id="${i+1}" data-name="Cerveja ${i+1}" data-category="cervejas" data-combo256="0" data-available256="1" data-price="4551" data-regular256="4790" data-max="3"><div class="menu-product-info"><small>Cervejas</small><p>Descrição</p><input data-product-quantity value="1"><button data-add>Adicionar</button></div></article>`).join('');
 await page.setContent(`<!doctype html><style>*{box-sizing:border-box}body{margin:0}[hidden]{display:none!important}${css}</style><body class="public-profile-area nu233-store nu232-store nu187-store-home"><template id="nu187-store-template"><section class="nu187-intro"><h1>Loja</h1></section></template><main data-native-menu data-carousel-layout="six"><div class="nu-menu-sticky"><div class="nu83-catalog-heading"><button class="nu168-trigger">☰</button><label class="nu83-search"><input data-product-search></label></div><nav class="menu-category-nav"><button data-category-filter="all">Todos</button><button data-category-filter="cervejas">Cervejas</button></nav></div><div class="menu-layout"><div class="menu-products">${cards}</div></div></main><script>window.NowUpCategory230={create:()=>document.createElement('span')};const counts={};window.NOWUP_CART160={quantity:id=>counts[id]||0,adjust(id,delta){counts[id]=Math.max(0,(counts[id]||0)+delta);window.dispatchEvent(new Event('nowup-cart-changed'))}};document.querySelectorAll('[data-add]').forEach(b=>b.addEventListener('click',()=>window.NOWUP_CART160.adjust(b.closest('[data-product]').dataset.id,1)));</script><script>${fs.readFileSync('static/storefront187.js','utf8')}</script>`);
 const section=page.locator('[data-category190="cervejas"]'),first=section.locator('.nu190-page').first(),card=first.locator('.nu493-quick').first(),plus=card.locator('.nu201-open'),step=card.locator('.nu-step263');
 await card.waitFor();assert.equal(await first.locator('.nu493-quick').count(),4);
 assert.equal(await first.evaluate(e=>getComputedStyle(e).gridTemplateColumns.split(' ').length),2);
 assert.ok(await section.locator('.nu471-carousel-next').first().isHidden());
 assert.equal(await plus.textContent(),'+');assert.equal(await plus.evaluate(e=>getComputedStyle(e).backgroundColor),'rgb(186, 250, 56)');
 await plus.click();assert.equal(await step.locator('span').textContent(),'1');assert.ok(await plus.isHidden());
 await step.locator('button').last().click();assert.equal(await step.locator('span').textContent(),'2');
 await step.locator('button').first().click();await step.locator('button').first().click();
 assert.ok(await step.isHidden());assert.ok(await plus.isVisible());
 assert.equal(await card.locator('.nu451-regular-price').evaluate(e=>getComputedStyle(e).backgroundColor),'rgba(0, 0, 0, 0)');
 }finally{await browser.close();}
});
