const test=require('node:test'), assert=require('node:assert/strict'), fs=require('node:fs');
const {chromium}=require('playwright');
const files=['storefront187','showcase190','category191','products201','products231','storefront232','offers256','original281','catalog-layout371','categories230','cart144','checkout-menu140','catalog-vertical493','vitrine-color494','catalog-unified496','vitrine-wide497','store-restore497','appearance505'];
const css=files.map(f=>fs.readFileSync('static/'+f+'.css','utf8')).join('\n');
const markup='<main id="nu312-catalog" class="native-menu nu496-unified" data-native-menu data-carousel-layout="three"><div class="nu190-showcase"><article class="nu201-card nu190-card nu493-quick"><div class="nu190-card-content"><div class="nu451-regular-price"><strong>R$ 3,50</strong></div></div><div class="nu-cart-actions262"><button id="add" class="nu201-open">Adicionar</button><div class="nu-step263"><button id="minus">−</button><span id="quantity">1</span><button>+</button></div></div></article></div><dialog class="checkout-dialog" data-checkout-dialog open><form data-order-form><label>Nome<input></label><b data-dialog-total>R$ 3,50</b><button class="btn primary" id="finish">Enviar pedido</button></form></dialog></main><dialog class="nu168-categories" open><header><div class="nu230-brand">NowUp<h2 id="nu168-title">Categorias</h2></div><button>×</button></header><nav><button><span class="nu230-icon">◯</span>Todos</button><button class="active"><span class="nu230-icon">★</span>Combos</button></nav></dialog><dialog class="nu143-cart-dialog" open><div class="panel"><b data-cart-total>R$ 3,50</b><button data-checkout>Continuar pedido</button></div></dialog>';
test('Sede palette wins on catalogue, drawer and checkout; original stays purple',async()=>{
 const browser=await chromium.launch({executablePath:process.env.NOWUP_CHROME_EXECUTABLE||undefined,args:['--no-sandbox']});
 try{
 for(const width of [390,1280]){
 const page=await browser.newPage({viewport:{width,height:844}});
 await page.setContent('<html data-appearance505="sede"><style>'+css+'</style><body class="public-profile-area public-menu-area nu233-store nu232-store sede-zero-price-theme">'+markup+'</body></html>');
 const prop=(sel,p)=>page.locator(sel).first().evaluate((e,p)=>getComputedStyle(e)[p],p);
 for(const sel of ['#add','#minus','#quantity','#finish','[data-checkout]','.nu168-categories>header']){
 assert.equal(await prop(sel,'backgroundColor'),'rgb(17, 17, 17)',sel);assert.equal(await prop(sel,'color'),'rgb(255, 255, 255)',sel);
 }
 for(const sel of ['.nu451-regular-price','[data-dialog-total]','[data-cart-total]','.nu168-categories nav .active']){
 assert.equal(await prop(sel,'backgroundColor'),'rgb(255, 218, 34)',sel);assert.equal(await prop(sel,'color'),'rgb(17, 17, 17)',sel);
 }
 assert.equal(await prop('#add','backgroundImage'),'none');
 assert.equal(await prop('.nu230-icon','color'),'rgb(17, 17, 17)');
 await page.evaluate(()=>document.documentElement.dataset.appearance505='original');
 assert.match(await prop('#add','backgroundImage'),/gradient/);
 assert.match(await prop('.nu168-categories>header','backgroundImage'),/gradient/);
 await page.close();
 }
 }finally{await browser.close()}
});
