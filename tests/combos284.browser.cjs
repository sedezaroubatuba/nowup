const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const {chromium}=require('playwright');
const read=p=>fs.readFileSync(p,'utf8');
const launch=()=>chromium.launch({headless:true,...(process.env.NOWUP_CHROME_EXECUTABLE?{executablePath:process.env.NOWUP_CHROME_EXECUTABLE}:{}),args:['--no-sandbox']});
test('combo card opens existing personalization directly, requires choices and commits selected values',async()=>{
 const browser=await launch();try{
 const page=await browser.newPage({viewport:{width:390,height:844}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 const config={ingredients:[],combo_items:[{name:'Energético',quantity:4}],groups:[{id:'drink',name:'Energético incluído',min:1,max:1,options:['Tradicional','Sem açúcar']}],utensils:false,notes:true};
 await page.setContent(`<!doctype html><style>[hidden]{display:none!important}.nu190-track{display:flex}.nu190-page{min-width:80%}${read('static/dishes151.css')}${read('static/offers256.css')}</style><body class="public-profile-area nu233-store"><template id="nu187-store-template"><section class="nu187-intro">Loja</section></template><main data-native-menu data-carousel-layout="compact"><div class="nu-menu-sticky"><div class="nu83-catalog-heading"><input data-product-search></div><nav class="menu-category-nav"><button data-category-filter="all">Todos</button></nav></div><div class="menu-layout"><article class="menu-product" data-product data-id="1" data-name="Combo teste" data-combo256="1" data-available256="1" data-dish="1" data-category="combos" data-price="25990" data-regular256="25990" data-max="99" data-custom192='${JSON.stringify(config)}'><div class="menu-product-info"><h3>Combo teste</h3><p>Descrição completa do combo</p><details class="nu85-note"><label>Observação<textarea data-product-notes></textarea></label></details><div class="product-buy"><input data-product-quantity value="1"><button data-add>Adicionar</button></div></div></article></div></main><script>window.NowUpCategory230={create:()=>document.createElement('span')};window.NOWUP_CART160={quantity:()=>0,commit:(card,drafts)=>window.committed284=drafts};</script><script>${read('static/custom196.js')}</script><script>${read('static/dishes151.js')}</script><script>${read('static/storefront187.js')}</script>`);
 await page.waitForSelector('.nu275-combo-card');assert.equal(await page.locator('.nu275-combo-section h2').textContent(),'Combos');assert.equal(await page.locator('.nu275-combo-card p').count(),0);
 await page.locator('.nu284-combo-open').click();assert.equal(await page.locator('.nu151-dish-dialog').isVisible(),true);assert.equal(await page.locator('.nu284-combo-items').textContent(),'O que vem no combo4 × Energético');
 await page.locator('.nu151-dish-dialog [data-add]').click();assert.match(await page.locator('[data-dish-error151]').textContent(),/Energético/);
 await page.getByLabel('Sem açúcar',{exact:true}).check();await page.locator('.nu151-dish-dialog [data-add]').click();
 assert.deepEqual(await page.evaluate(()=>window.committed284[0].customization.groups.drink),['Sem açúcar']);assert.equal(await page.locator('.nu151-dish-dialog').isVisible(),false);assert.deepEqual(errors,[]);
 }finally{await browser.close();}
});
test('combo registration exposes item quantities and preserves them on submit',async()=>{
 const browser=await launch();try{
 const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.setContent(`<!doctype html><div class="pro-dashboard"><form><label>Categoria<select name="category"><option value="Geral">Geral</option><option value="__combos256">Combos</option></select></label><input name="description" value="Descrição do combo"><label>Adicionais<select name="extras_mode"><option value="none">Sem adicionais</option></select></label><div data-editor192=""><h3>Personalização</h3></div><button type="submit">Salvar</button></form></div><script>${read('static/custom196.js')}</script><script>${read('static/compact200.js')}</script><script>document.querySelector('form').addEventListener('submit',e=>{e.preventDefault();window.saved284=JSON.parse(new FormData(e.target).get('customization192'));});</script>`);
 await page.selectOption('[name=category]','__combos256');await page.getByRole('button',{name:'+ Adicionar item',exact:true}).click();await page.getByLabel('Item do combo',{exact:true}).fill('Red Bull');await page.getByLabel('Quantidade incluída',{exact:true}).fill('4');await page.getByRole('button',{name:'Salvar',exact:true}).click();
 assert.deepEqual(await page.evaluate(()=>window.saved284.combo_items),[{name:'Red Bull',quantity:4}]);assert.deepEqual(errors,[]);
 }finally{await browser.close();}
});
