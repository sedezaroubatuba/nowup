const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const {chromium}=require('playwright');
test('mobile shelf has four products, green counter and no horizontal arrows',async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.NOWUP_CHROME_EXECUTABLE||undefined,args:['--no-sandbox']});
 try{
 const page=await browser.newPage({viewport:{width:390,height:844}});
 const css=['storefront187','showcase190','category191','products201','products231','storefront232','offers256','original281','catalog-layout371','catalog-vertical493','vitrine-color494'].map(f=>fs.readFileSync('static/'+f+'.css','utf8')).join('\n');
 const cards=Array.from({length:5},(_,i)=>`<article class="menu-product" data-product data-id="${i+1}" data-name="Cerveja ${i+1}" data-category="cervejas" data-combo256="0" data-available256="1" data-price="4551" data-regular256="4790" data-max="3"><div class="menu-product-info"><small>Cervejas</small><p>Descrição</p><input data-product-quantity value="1"><button data-add>Adicionar</button></div></article>`).join('');
 await page.setContent(`<!doctype html><style>*{box-sizing:border-box}body{margin:0}[hidden]{display:none!important}${css}</style><body class="public-profile-area nu233-store nu232-store nu187-store-home"><template id="nu187-store-template"><section class="nu187-intro"><h1>Loja</h1></section></template><main data-native-menu data-carousel-layout="compact"><div class="nu-menu-sticky"><div class="nu83-catalog-heading"><button class="nu168-trigger">☰</button><label class="nu83-search"><input data-product-search></label></div><nav class="menu-category-nav"><button data-category-filter="all">Todos</button><button data-category-filter="cervejas">Cervejas</button></nav></div><div class="menu-layout"><div class="menu-products">${cards}</div></div></main><script>window.NowUpCategory230={create:()=>document.createElement('span')};const counts={};window.NOWUP_CART160={quantity:id=>counts[id]||0,adjust(id,delta){counts[id]=Math.max(0,(counts[id]||0)+delta);window.dispatchEvent(new Event('nowup-cart-changed'))}};document.querySelectorAll('[data-add]').forEach(b=>b.addEventListener('click',()=>window.NOWUP_CART160.adjust(b.closest('[data-product]').dataset.id,1)));</script><script>${fs.readFileSync('static/storefront187.js','utf8')}</script>`);
 const section=page.locator('[data-category190="cervejas"]'),first=section.locator('.nu190-page').first(),card=first.locator('.nu493-quick').first(),plus=card.locator('.nu201-open'),step=card.locator('.nu-step263');
 await card.waitFor();assert.equal(await first.locator('.nu493-quick').count(),4);
 assert.equal(await first.evaluate(e=>getComputedStyle(e).gridTemplateColumns.split(' ').length),2);
 assert.ok(await section.locator('.nu471-carousel-next').first().isHidden());
 assert.equal(await plus.textContent(),'+');assert.equal(await plus.evaluate(e=>getComputedStyle(e).fontSize),'0px');await plus.evaluate(e=>e.textContent='Adicionar');assert.match(await plus.evaluate(e=>getComputedStyle(e,'::after').content),/\+/);assert.equal(await plus.evaluate(e=>getComputedStyle(e).backgroundColor),'rgb(186, 250, 56)');
 await plus.click();assert.equal(await step.locator('span').textContent(),'1');assert.ok(await plus.isHidden());
 await step.locator('button').last().click();assert.equal(await step.locator('span').textContent(),'2');
 await step.locator('button').first().click();await step.locator('button').first().click();
 assert.ok(await step.isHidden());assert.ok(await plus.isVisible());
 assert.equal(await card.locator('.nu451-regular-price').evaluate(e=>getComputedStyle(e).backgroundColor),'rgba(0, 0, 0, 0)');
 }finally{await browser.close();}
});

test('home marketplace fits four products in one swipeable row on a narrow phone',async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.NOWUP_CHROME_EXECUTABLE||undefined,args:['--no-sandbox']});
 try{
 const page=await browser.newPage({viewport:{width:390,height:844}});
 const css=['vitrine473','original281','catalog-vertical493','vitrine-color494'].map(f=>fs.readFileSync('static/'+f+'.css','utf8')).join('\n');
 const items=Array.from({length:8},(_,i)=>`<article><div class="vitrine-product-card"><a class="vitrine-product-detail"><img alt="" width="144" height="110"><h3>Chocolate ${i}</h3><strong>R$ 5,49</strong></a><button class="vitrine-view-product" data-vitrine-item='${JSON.stringify({id:i+1,name:'Chocolate '+i,price:549,max:9,slug:'sede-zero',store:'Sede Zero',options:false})}'>Adicionar</button></div></article>`).join('');
 await page.setContent(`<style>*{box-sizing:border-box}body{margin:0}[hidden]{display:none!important}${css}</style><body class="v50-directory-home vitrine-launch"><main class="vitrine-home" data-vitrine><span data-vitrine-status></span><div data-nu494-scroll data-page-size="4" class="vitrine-products">${items}</div><div class="nu494-dots"></div></main><script>${fs.readFileSync('static/vitrine473.js','utf8')}</script>`);
 const track=page.locator('.vitrine-products'),card=track.locator('article').first(),button=card.locator('.vitrine-view-product');
 const first=await card.boundingBox(),fourth=await track.locator('article').nth(3).boundingBox(),fifth=await track.locator('article').nth(4).boundingBox(),box=await track.boundingBox();
 assert.equal(first.y,fourth.y);assert.ok(fourth.x+fourth.width<=box.x+box.width+1);assert.ok(fifth.x>=box.x+box.width-1);
 assert.equal(await button.evaluate(e=>getComputedStyle(e).fontSize),'0px');assert.ok(await button.evaluate(e=>getComputedStyle(e,'::after').content.includes('+')));
 }finally{await browser.close();}
});
