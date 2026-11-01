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
 await page.setContent(`<!doctype html><script type="application/json" id="combo-catalog298">[{"id":1,"name":"Red Bull","available":true}]</script><div class="pro-dashboard"><form><label>Categoria<select name="category"><option value="Geral">Geral</option><option value="__combos256">Combos</option></select></label><input name="description" value="Descrição do combo"><label>Adicionais<select name="extras_mode"><option value="none">Sem adicionais</option></select></label><div data-editor192=""><h3>Personalização</h3></div><button type="submit">Salvar</button></form></div><script>${read('static/custom196.js')}</script><script>${read('static/compact200.js')}</script><script>document.querySelector('form').addEventListener('submit',e=>{e.preventDefault();window.saved284=JSON.parse(new FormData(e.target).get('customization192'));});</script>`);
 await page.selectOption('[name=category]','__combos256');await page.getByRole('button',{name:'+ Adicionar item',exact:true}).click();await page.getByLabel('Pesquisar produto da loja',{exact:true}).fill('Red Bull · #1');await page.getByLabel('Quantidade incluída',{exact:true}).fill('4');await page.getByRole('button',{name:'Salvar',exact:true}).click();
 assert.deepEqual(await page.evaluate(()=>window.saved284.combo_items),[{product_id:1,name:'Red Bull',quantity:4}]);assert.deepEqual(errors,[]);
 }finally{await browser.close();}
});


test('mobile combo search shows store products and saves the selected product ID',async()=>{
 const browser=await launch();try{
 const page=await browser.newPage({viewport:{width:390,height:844}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.setContent(`<!doctype html><meta name="viewport" content="width=device-width"><style>[hidden]{display:none!important}${read('static/custom196.css')}</style><script type="application/json" id="combo-catalog298">[{"id":1,"name":"Red Bull 250 ml","available":true},{"id":2,"name":"Gelo de coco","available":true},{"id":3,"name":"Produto esgotado","available":false}]</script><form><select name="category"><option value="__combos256">Combos</option></select><input name="description" value="Acompanha copos e canudos"><select name="extras_mode"><option value="none">Sem adicionais</option></select><div class="nu192-editor" data-editor192=""></div><button type="submit">Salvar</button></form><script>${read('static/custom196.js')}</script><script>document.querySelector('form').addEventListener('submit',e=>{e.preventDefault();window.saved300=JSON.parse(new FormData(e.target).get('customization192'));});</script>`);
 await page.getByRole('button',{name:'+ Adicionar item',exact:true}).click();
 const input=page.getByLabel('Pesquisar produto da loja',{exact:true});await input.fill('Red');
 const result=page.locator('[data-select-product300="1"]');assert.equal(await result.isVisible(),true);assert.equal(await page.locator('[data-select-product300="3"]').count(),0);
 const bounds=await result.boundingBox();assert.ok(bounds.width>250&&bounds.x>=0&&bounds.x+bounds.width<=390,JSON.stringify(bounds));
 await result.click();assert.equal(await input.inputValue(),'Red Bull 250 ml · #1');await page.getByLabel('Quantidade incluída',{exact:true}).fill('4');
 await page.getByRole('button',{name:'Salvar',exact:true}).click();assert.deepEqual(await page.evaluate(()=>window.saved300.combo_items),[{product_id:1,name:'Red Bull 250 ml',quantity:4}]);
 await input.fill('inexistente');assert.equal(await page.getByText('Nenhum produto encontrado. Tente outro nome.').isVisible(),true);
 assert.deepEqual(errors,[]);
 }finally{await browser.close();}
});

test('dedicated combo form imports store products, offers quantities and manual accessories',async()=>{
 const browser=await launch();try{
 const page=await browser.newPage({viewport:{width:390,height:844}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.setContent(`<!doctype html><style>[hidden]{display:none!important}${read('static/custom196.css')}</style><div class="pro-dashboard"><section id="combos-loja"><h2>Cadastrar combo</h2><form data-combo-editor301="1"><input type="hidden" name="category" value="__combos256"><input name="name" value="Combo teste"><div class="nu192-editor" data-editor192=""></div><button type="submit">Salvar combo</button></form></section></div><script type="application/json" id="combo-catalog298">[{"id":1,"name":"Red Bull","available":true},{"id":2,"name":"Red Bull sem açúcar","available":true},{"id":3,"name":"Gelo de coco","available":true}]</script><script>${read('static/combo-editor301.js')}</script><script>${read('static/custom196.js')}</script><script>${read('static/compact200.js')}</script><script>document.querySelector('form').addEventListener('submit',e=>{e.preventDefault();window.combo301=JSON.parse(new FormData(e.target).get('customization192'));});</script>`);
 await page.getByRole('button',{name:'+ Adicionar grupo de escolhas',exact:true}).click();
 await page.getByLabel('Nome do grupo de escolhas',{exact:true}).fill('Energéticos');await page.getByLabel('Unidades incluídas neste grupo',{exact:true}).fill('4');
 const search=page.getByLabel('Buscar produto para o combo',{exact:true});await search.fill('Red');await page.locator('[data-import-product301="1"]').click();await search.fill('sem');await page.locator('[data-import-product301="2"]').click();await page.getByLabel('Unidades incluídas neste grupo',{exact:true}).fill('4');
 await page.getByRole('button',{name:'+ Adicionar item manual',exact:true}).click();await page.getByLabel('Nome do item manual',{exact:true}).fill('Copo');await page.getByLabel('Quantidade do item manual',{exact:true}).fill('4');
 await page.getByRole('button',{name:'Salvar combo',exact:true}).click();const config=await page.evaluate(()=>window.combo301);assert.equal(config.combo_items[0].product_id,1);assert.equal(config.combo_items[0].quantity,4);assert.deepEqual(config.groups[0].product_ids,[1,2]);assert.equal(config.groups[0].name,'Energéticos');assert.equal(config.groups[0].max,4);assert.deepEqual(config.combo_manual,[{name:'Copo',quantity:4}]);assert.equal(await page.locator('.nu200-question').count(),0);assert.deepEqual(errors,[]);
 }finally{await browser.close();}
});
test('customer distributes four units between flavors and cannot exceed the combo limit',async()=>{
 const browser=await launch();try{
 const page=await browser.newPage({viewport:{width:390,height:844}}),config={ingredients:[],combo_items:[{name:'Red Bull',quantity:4}],combo_manual:[{name:'Copo',quantity:4}],groups:[{id:'drink','name':'Energéticos','min':4,'max':4,'options':['Red Bull','Red Bull sem açúcar'],'product_ids':[1,2],quantity_mode:true}],utensils:false,notes:true};
 await page.setContent(`<!doctype html><style>[hidden]{display:none!important}${read('static/custom196.css')}</style><article class="menu-product nu151-dish-open" data-product data-id="1" data-combo256="1" data-custom192='${JSON.stringify(config)}'><div class="product-buy"></div></article><script>${read('static/custom196.js')}</script>`);
 await page.getByRole('button',{name:'Aumentar Red Bull',exact:true}).click();await page.getByRole('button',{name:'Aumentar Red Bull',exact:true}).click();await page.getByRole('button',{name:'Aumentar Red Bull sem açúcar',exact:true}).click();await page.getByRole('button',{name:'Aumentar Red Bull sem açúcar',exact:true}).click();
 assert.equal(await page.getByLabel('Quantidade de Red Bull',{exact:true}).inputValue(),'2');assert.equal(await page.getByLabel('Quantidade de Red Bull sem açúcar',{exact:true}).inputValue(),'2');assert.equal(await page.getByRole('button',{name:'Aumentar Red Bull',exact:true}).isDisabled(),true);
 const snap=await page.evaluate(()=>{const card=document.querySelector('[data-product]'),customization=window.NOWUP_CUSTOM192.snapshot(card);window.NOWUP_CUSTOM192.validate(card,{options:[],customization});return customization;});assert.deepEqual(snap.groups.drink,['Red Bull','Red Bull','Red Bull sem açúcar','Red Bull sem açúcar']);assert.equal(await page.getByText('4 × Copo',{exact:true}).count(),1);
 }finally{await browser.close();}
});


test('product combo switch keeps category and computes current catalog savings without charging again',async()=>{
 const browser=await launch();try{
 const page=await browser.newPage({viewport:{width:390,height:844}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.setContent(`<!doctype html><div class="pro-dashboard"><form><label>Este produto é um combo?<select name="is_combo256" data-combo-type303><option value="0">Não</option><option value="1">Sim</option></select></label><select name="category"><option>Combos de whisky</option></select><label>Preço<input name="price" value="30,00"></label><select name="extras_mode"><option value="none">Sem adicionais</option></select><div class="nu192-editor" data-editor192=""></div><button type="submit">Salvar produto</button></form></div><script type="application/json" id="combo-catalog298">[{"id":1,"name":"Red Bull","available":true,"unit_price_cents":1000}]</script><script>${read('static/combo-prices303.js')}</script><script>${read('static/combo-editor301.js')}</script><script>${read('static/custom196.js')}</script><script>${read('static/compact200.js')}</script><script>document.querySelector('form').addEventListener('submit',e=>{e.preventDefault();window.saved304=Object.fromEntries(new FormData(e.target));window.payloadCount304=new FormData(e.target).getAll('customization192').length;});</script>`);
 await page.selectOption('[data-combo-type303]','1');await page.getByRole('button',{name:'+ Adicionar grupo de escolhas',exact:true}).click();await page.getByLabel('Nome do grupo de escolhas',{exact:true}).fill('Energéticos');await page.getByLabel('Unidades incluídas neste grupo',{exact:true}).fill('4');await page.getByLabel('Buscar produto para o combo',{exact:true}).fill('Red');await page.locator('[data-import-product301="1"]').click();assert.match(await page.locator('[data-switch-combo303] .nu303-comparison').textContent(),/10,00/);
 await page.getByRole('button',{name:'Salvar produto',exact:true}).click();let saved=await page.evaluate(()=>window.saved304);assert.equal(saved.category,'Combos de whisky');assert.equal(saved.price,'30,00');assert.equal(saved.is_combo256,'1');assert.equal(await page.evaluate(()=>window.payloadCount304),1);assert.equal(JSON.parse(saved.customization192).groups[0].max,4);
 await page.selectOption('[data-combo-type303]','0');await page.getByRole('button',{name:'Salvar produto',exact:true}).click();assert.equal(await page.evaluate(()=>window.saved304.is_combo256),'0');assert.equal(await page.evaluate(()=>window.payloadCount304),1);assert.deepEqual(errors,[]);
 }finally{await browser.close();}
});
test('combo comparison follows selected flavors and excludes manual freebies',async()=>{
 const browser=await launch();try{
 const page=await browser.newPage({viewport:{width:390,height:844}});
 const config={ingredients:[],combo_items:[{product_id:1,name:'Red Bull',quantity:4,group_id301:'drink'}],combo_manual:[{name:'Canudo',quantity:4}],groups:[{id:'drink',name:'Energéticos',min:4,max:4,options:['Normal','Zero'],product_ids:[1,2],quantity_mode:true}],utensils:false,notes:true};
 await page.setContent(`<!doctype html><article class="menu-product nu151-dish-open" data-product data-id="1" data-combo256="1" data-price="3000" data-combo-prices303='{"1":1000,"2":1200}' data-custom192='${JSON.stringify(config)}'><div class="menu-product-info"><h3>Combo</h3><div class="product-buy"></div></div></article><script>${read('static/combo-prices303.js')}</script><script>${read('static/custom196.js')}</script>`);
 assert.match(await page.locator('[data-comparison303]').textContent(),/a partir de/);
 await page.getByRole('button',{name:'Aumentar Normal',exact:true}).click();await page.getByRole('button',{name:'Aumentar Normal',exact:true}).click();await page.getByRole('button',{name:'Aumentar Zero',exact:true}).click();await page.getByRole('button',{name:'Aumentar Zero',exact:true}).click();
 await page.evaluate(()=>window.NOWUP_CUSTOM192.snapshot(document.querySelector('[data-product]')));assert.match(await page.locator('[data-comparison303]').textContent(),/44,00/);assert.match(await page.locator('[data-comparison303]').textContent(),/14,00/);assert.doesNotMatch(await page.locator('[data-comparison303]').textContent(),/a partir de/);
 }finally{await browser.close();}
});


test('principal is fixed and singleton groups need no customer selection',async()=>{
 const browser=await launch();try{
 const page=await browser.newPage();const config={ingredients:[],combo_items:[{product_id:1,name:'Whisky',quantity:1,principal:true},{product_id:2,name:'Red Bull',quantity:4,group_id301:'drink'}],groups:[{id:'drink',name:'Energéticos',min:4,max:4,quantity_mode:true,options:['Red Bull'],product_ids:[2]}],combo_manual:[],notes:true};
 await page.setContent(`<article data-product data-combo256="1" data-custom192='${JSON.stringify(config)}'><div class="product-buy"></div></article><script>${read('static/custom196.js')}</script>`);
 assert.equal(await page.getByText('Produto principal: 1 × Whisky',{exact:true}).count(),1);
 assert.equal(await page.getByRole('button',{name:'Aumentar Red Bull',exact:true}).count(),0);
 const snap=await page.evaluate(()=>{const c=document.querySelector('[data-product]'),s=window.NOWUP_CUSTOM192.snapshot(c);window.NOWUP_CUSTOM192.validate(c,{customization:s,options:[]});return s;});assert.deepEqual(snap.groups.drink,['Red Bull','Red Bull','Red Bull','Red Bull']);
 }finally{await browser.close();}
});
test('compact combo cart keeps full choices and a single line price',async()=>{
 const browser=await launch();try{
 const page=await browser.newPage();await page.route('https://nowup.test/**',r=>r.fulfill({body:'<!doctype html>'}));await page.goto('https://nowup.test/p/loja/menu');
 const config={combo_items:[{product_id:1,name:'Whisky',quantity:1,principal:true},{name:'Red Bull',quantity:4,group_id301:'drink'}],groups:[{id:'drink',name:'Energéticos',options:['Normal','Zero']}],combo_manual:[{name:'Canudo',quantity:4}]};
 await page.evaluate(()=>{window.NOWUP_MENU={customerId:1,open:true};localStorage.setItem('nowup-cart:u:1:/p/loja',JSON.stringify([['100:a',{productId:100,name:'Combo whisky',unitPrice:15000,quantity:1,options:[],customization:{groups:{drink:['Normal','Normal','Zero','Zero']}},customizationSummary:'Energéticos: 2 × Normal, 2 × Zero',max:99}]]));});
 await page.setContent(`<main data-native-menu><article data-product data-id="100" data-dish="1" data-combo256="1" data-custom192='${JSON.stringify(config)}'></article><div data-cart-items></div><span data-cart-total></span><button data-checkout></button></main><dialog data-checkout-dialog></dialog><script>${read('static/menu88.js')}</script>`);
 assert.equal(await page.locator('.cart-item .nu305-line-price').count(),1);assert.match(await page.locator('.nu305-combo-summary').textContent(),/Principal: 1 × Whisky/);assert.equal(await page.getByRole('button',{name:'Editar combo',exact:true}).count(),1);
 await page.getByText('Ver itens escolhidos',{exact:true}).click();assert.equal(await page.getByText('Energéticos: 2 × Normal, 2 × Zero',{exact:true}).isVisible(),true);assert.equal(await page.locator('.cart-item').textContent().then(s=>(s.match(/150,00/g)||[]).length),1);
 await page.locator('[data-plus]').click();assert.match(await page.locator('.nu305-line-price').textContent(),/300,00/);assert.equal(await page.locator('[data-cart-quantity]').inputValue(),'2');
 }finally{await browser.close();}
});


require('./pairs256.test.cjs');
async function cartPreview310(browser,width=390){
 const page=await browser.newPage({viewport:{width,height:844}});await page.route('https://cart310.test/**',r=>r.fulfill({body:'<!doctype html>'}));await page.goto('https://cart310.test/p/loja/menu');
 await page.evaluate(()=>{window.NOWUP_MENU={customerId:1,open:true};localStorage.setItem('nowup-cart:u:1:/p/loja',JSON.stringify([['1:base',{productId:1,name:'Compra principal',unitPrice:1000,quantity:1,options:[],max:99}]]));});
 const products=Array.from({length:9},(_,i)=>{const id=i+1;return `<article hidden data-product data-id="${id}" data-name="Produto ${id}" data-price="${id===1?1000:id*100}" data-max="99" data-dish="0" data-available256="${id===3?0:1}" data-recommend256="${id===1?0:1}"><input data-product-quantity value="1"><button data-add>Adicionar</button></article>`;}).join('');
 await page.setContent(`<style>*{box-sizing:border-box}body{margin:0}dialog{width:calc(100vw - 24px);max-width:860px;padding:12px;border:0}${read('static/offers256.css')}${read('static/pairs310.css')}</style><main data-native-menu>${products}<dialog data-cart-dialog143><div data-cart-items></div><span data-cart-total></span><button data-checkout>Continuar pedido</button></dialog></main><dialog data-checkout-dialog></dialog><script>${read('static/menu88.js')}</script><script>${read('static/pairs256.js')}</script>`);
 await page.evaluate(()=>document.querySelector('[data-cart-dialog143]').showModal());await page.waitForSelector('.nu256-pair');return page;
}
test('cart suggestions cap at five, scroll sideways and only charge after Add',async()=>{
 const browser=await launch();try{for(const width of [320,390,1000]){
 const page=await cartPreview310(browser,width),errors=[];page.on('pageerror',e=>errors.push(e.message));
 assert.equal(await page.locator('.nu256-pair').count(),5);assert.deepEqual(await page.locator('.nu256-pair').evaluateAll(rows=>rows.map(r=>r.dataset.pair310)),['2','4','5','6','7']);assert.equal(await page.locator('.cart-item').count(),1);assert.match(await page.locator('[data-cart-total]').textContent(),/10,00/);
 const track=page.locator('.nu310-pair-track');assert.ok(await track.evaluate(e=>e.scrollWidth>e.clientWidth));assert.equal(await track.evaluate(e=>getComputedStyle(e).overflowX),'auto');
 const bounds=await page.locator('[data-cart-dialog143]').boundingBox();assert.ok(bounds.x>=0&&bounds.x+bounds.width<=width+1,JSON.stringify(bounds));
 await page.getByRole('button',{name:'Ver sugestão 5: Produto 7',exact:true}).click();await page.waitForFunction(()=>{const track=document.querySelector('.nu310-pair-track');return track.scrollLeft+track.clientWidth>=track.scrollWidth-2&&document.querySelector('.nu310-pair-counter').textContent==='5/5';});
 await page.getByRole('button',{name:'Ver sugestão 1: Produto 2',exact:true}).click();await page.waitForTimeout(350);
 await page.getByRole('button',{name:'Adicionar Produto 2',exact:true}).click();await page.waitForFunction(()=>document.querySelectorAll('.cart-item').length===2);
 assert.match(await page.locator('[data-cart-total]').textContent(),/12,00/);await page.waitForFunction(()=>!document.querySelector('[data-pair310="2"]'));assert.equal(await page.locator('.nu256-pair').count(),5);assert.deepEqual(errors,[]);await page.close();
 }}finally{await browser.close();}
});
test('suggested personalized product uses its existing chooser before adding',async()=>{
 const browser=await launch();try{
 const page=await cartPreview310(browser);await page.evaluate(()=>{const card=document.querySelector('[data-product][data-id="2"]');card.dataset.dish='1';const choose=document.createElement('button');choose.className='nu151-choose';choose.onclick=()=>window.chooser310=true;card.append(choose);});
 await page.getByRole('button',{name:'Adicionar Produto 2',exact:true}).click();assert.equal(await page.evaluate(()=>window.chooser310),true);assert.equal(await page.evaluate(()=>window.NOWUP_CART160.quantity(2)),0);assert.match(await page.locator('[data-cart-total]').textContent(),/10,00/);
 }finally{await browser.close();}
});
