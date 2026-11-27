const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const {chromium}=require('playwright');
test('restored store has purple add buttons and working subcategory selection',async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.NOWUP_CHROME_EXECUTABLE||undefined,args:['--no-sandbox']});
 try{
 const page=await browser.newPage({viewport:{width:390,height:844}});
 const css=['storefront187','showcase190','category191','products201','products231','storefront232','offers256','original281','catalog-layout371','store-restore497'].map(f=>fs.readFileSync('static/'+f+'.css','utf8')).join('\n');
 const cards=Array.from({length:5},(_,i)=>`<article class="menu-product" data-product data-id="${i+1}" data-name="Produto ${i+1}" data-category="bebidas" data-subcategory261="${i%2?2:1}" data-combo256="0" data-available256="1" data-price="4551" data-regular256="4790" data-max="3"><div class="menu-product-info"><small>Bebidas</small><p>Descrição</p><input data-product-quantity value="1"><button data-add>Adicionar</button></div></article>`).join('');
 await page.setContent(`<!doctype html><style>*{box-sizing:border-box}body{margin:0}[hidden]{display:none!important}${css}</style><body class="public-profile-area nu233-store nu232-store nu187-store-home"><template id="nu187-store-template"><section class="nu187-intro"><h1>Loja</h1></section></template><main data-native-menu data-carousel-layout="compact"><span data-scid261="1" data-parent261="bebidas" data-name261="Fardos"></span><span data-scid261="2" data-parent261="bebidas" data-name261="Unidades"></span><div class="nu-menu-sticky"><div class="nu83-catalog-heading"><button class="nu168-trigger">☰</button><label class="nu83-search"><input data-product-search></label></div><nav class="menu-category-nav"><button data-category-filter="all">Todos</button><button data-category-filter="bebidas">Bebidas</button></nav></div><div class="menu-layout"><div class="menu-products">${cards}</div></div></main><script>window.NowUpCategory230={create:()=>document.createElement('span')};const counts={};window.NOWUP_CART160={quantity:id=>counts[id]||0,adjust(id,delta){counts[id]=Math.max(0,(counts[id]||0)+delta);window.dispatchEvent(new Event('nowup-cart-changed'))}};document.querySelectorAll('[data-add]').forEach(b=>b.addEventListener('click',()=>window.NOWUP_CART160.adjust(b.closest('[data-product]').dataset.id,1)));</script><script>${fs.readFileSync('static/storefront187.js','utf8')}</script>`);
 const section=page.locator('[data-category190="bebidas"]'),card=section.locator('.nu190-card').first(),add=card.locator('.nu201-open');
 await card.waitFor();assert.equal(await add.textContent(),'Adicionar');assert.equal(await card.evaluate(e=>getComputedStyle(e).borderTopColor),'rgb(118, 43, 192)');assert.match(await card.evaluate(e=>getComputedStyle(e).boxShadow),/255, 120, 40/);assert.match(await add.evaluate(e=>getComputedStyle(e).backgroundImage),/gradient/);
 await add.click();assert.equal(await card.locator('.nu-step263 span').textContent(),'1');assert.ok(await add.isHidden());assert.equal(await card.evaluate(e=>getComputedStyle(e).borderTopColor),'rgb(118, 43, 192)');assert.match(await card.evaluate(e=>getComputedStyle(e).boxShadow),/255, 120, 40/);
 await section.locator('header button').click();
 const filters=page.locator('.nu465-subcategories');await filters.getByRole('button',{name:'Unidades'}).click();
 assert.equal(await page.locator('.nu191-grid:visible .nu190-card:visible').count(),2);
 await filters.getByRole('button',{name:'Fardos'}).click();assert.equal(await page.locator('.nu191-grid:visible .nu190-card:visible').count(),3);
 await filters.getByRole('button',{name:'Todos da categoria'}).click();assert.equal(await page.locator('.nu191-grid:visible .nu190-card:visible').count(),5);
 }finally{await browser.close();}
});
test('home marketplace fits four products in one swipeable row on a narrow phone',async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.NOWUP_CHROME_EXECUTABLE||undefined,args:['--no-sandbox']});
 try{
 const page=await browser.newPage({viewport:{width:390,height:844}});
 const css=['vitrine473','original281','catalog-vertical493','vitrine-color494','catalog-unified496','vitrine-wide497'].map(f=>fs.readFileSync('static/'+f+'.css','utf8')).join('\n');
 const items=Array.from({length:8},(_,i)=>`<article><div class="vitrine-product-card"><a class="vitrine-product-detail"><img alt="" width="144" height="110"><h3>Chocolate ${i}</h3><strong>R$ 5,49</strong></a><button class="vitrine-view-product" data-vitrine-item='${JSON.stringify({id:i+1,name:'Chocolate '+i,price:549,max:9,slug:'sede-zero',store:'Sede Zero',options:false})}'>Adicionar</button></div></article>`).join('');
 await page.setContent(`<style>*{box-sizing:border-box}body{margin:0}[hidden]{display:none!important}${css}</style><body class="v50-directory-home vitrine-launch"><main class="vitrine-home" data-vitrine><span data-vitrine-status></span><div data-nu494-scroll data-page-size="4" class="vitrine-products">${items}</div><div class="nu494-dots"></div></main><script>${fs.readFileSync('static/vitrine473.js','utf8')}</script>`);
 const track=page.locator('.vitrine-products'),card=track.locator('article').first(),button=card.locator('.vitrine-view-product');
 const first=await card.boundingBox(),fourth=await track.locator('article').nth(3).boundingBox(),fifth=await track.locator('article').nth(4).boundingBox(),box=await track.boundingBox();
 assert.equal(first.y,fourth.y);assert.ok(fourth.x+fourth.width<=box.x+box.width+1);assert.ok(fifth.x>=box.x+box.width-1);
 assert.equal(await button.evaluate(e=>getComputedStyle(e).fontSize),'0px');assert.ok(await button.evaluate(e=>getComputedStyle(e,'::after').content.includes('+')));
 }finally{await browser.close();}
});
test('desktop marketplace spans the legacy sidebar grid without clipping banners or categories',async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.NOWUP_CHROME_EXECUTABLE||undefined,args:['--no-sandbox']});
 try{
 const page=await browser.newPage({viewport:{width:1366,height:900}});
 const base=fs.readFileSync('templates/base.html','utf8');
 const legacy=base.match(/html body\.v50-directory-home \.v50-home\{display:grid!important;[^}]+\}/)[0];
 const css=['v50-directory','vitrine473','catalog-vertical493','vitrine-color494','catalog-unified496','vitrine-wide497'].map(f=>fs.readFileSync('static/'+f+'.css','utf8')).join('\n');
 await page.setContent(`<style>*{box-sizing:border-box}body{margin:0}${legacy}${css}</style><body class="v50-directory-home vitrine-launch"><main class="v50-home"><div class="vitrine-home container"><div class="nu494-hero-track"><a class="nu494-hero nu500-promo-single"><div class="nu500-promo-copy"><strong>PROMOÇÕES<br><em>DA SEMANA</em></strong><small>Cerveja Skol</small><b class="nu498-combo-price">R$ 45,51</b></div><div class="nu494-hero-photos"></div></a></div><nav class="nu494-shortcuts">${['Promoções','Cervejas','Refrigerantes','Mercearia','Chocolates'].map(t=>'<a><span>+</span><b>'+t+'</b></a>').join('')}</nav><div class="vitrine-products">${'<article>Produto</article>'.repeat(5)}</div></div></main>`);
 const home=await page.locator('.vitrine-home').boundingBox();
 assert.ok(home.width>1000);assert.ok(Math.abs(home.x-(1366-home.width)/2)<2);
 const hero=await page.locator('.nu494-hero').boundingBox();assert.ok(hero.width>950);
 const icons=await page.locator('.nu494-shortcuts a').evaluateAll(es=>es.map(e=>({left:e.offsetLeft,width:e.offsetWidth})));
 for(let i=1;i<icons.length;i++)assert.ok(icons[i].left>=icons[i-1].left+icons[i-1].width);
 const cards=await page.locator('.vitrine-products article').evaluateAll(es=>es.map(e=>e.getBoundingClientRect().toJSON()));
 assert.equal(cards[0].y,cards[3].y);assert.ok(cards[3].right<=hero.x+hero.width+1);assert.ok(cards[4].left>=hero.x+hero.width-1);
 }finally{await browser.close();}
});
