const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),{chromium}=require('playwright');
const read=p=>fs.readFileSync(path.join(__dirname,'..',p),'utf8');
const fixture=`<html><body><main data-native-menu data-login-required252="0"><article data-product data-id="1"></article><aside class="menu-cart"><div data-cart-items></div><b data-cart-total></b><button data-checkout>Continuar</button></aside><dialog data-checkout-dialog><form action="/p/shop/menu/whatsapp" method="post"><input name="customer_name" value="Maria"><input name="cart_json" data-cart-json><select name="fulfillment_type" data-fulfillment><option value="pickup">Retirar</option></select><select name="payment_method" data-payment><option value="pix">Pix</option></select><b data-dialog-total></b><button type="submit">Finalizar</button></form></dialog></main></body></html>`;
for(const mode of ['panel','whatsapp','both'])test('configured '+mode+' shows the correct next step and cart lifecycle',async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.NOWUP_CHROME_EXECUTABLE?{executablePath:process.env.NOWUP_CHROME_EXECUTABLE}:{})});const page=await browser.newPage();page.setDefaultTimeout(8000);let requests=0;
 try{
 await page.route('https://nowup.local/**',r=>{if(r.request().url().endsWith('/menu/whatsapp')){requests++;return r.fulfill({json:{prepared:true,recorded:mode!=='whatsapp',mode,message:'Cliente: Maria\nPedido NU-000001',order_code:'NU-000001',...(mode!=='panel'?{whatsapp_url:'https://wa.me/5512999999999?text=Pedido'}:{}),...(mode!=='whatsapp'?{redirect:'/p/shop/pedido/token257'}:{})}});}return r.fulfill({contentType:'text/html',body:fixture});});
 await page.goto('https://nowup.local/p/shop/menu?loja=1');await page.evaluate(()=>{window.NOWUP_MENU={customerId:10,open:true,whatsappCheckout:true};localStorage.setItem('nowup-cart:whatsapp257:u:10:/p/shop',JSON.stringify([['1',{productId:1,name:'Produto',unitPrice:300,quantity:2,options:[],max:99}]]));});
 await page.addScriptTag({content:read('static/menu88.js')});await page.locator('[data-checkout]').click();await page.getByRole('button',{name:'Finalizar',exact:true}).click();await page.locator('[data-whatsapp-ready257]').waitFor();
 assert.equal(await page.getByRole('link',{name:'Abrir WhatsApp e enviar'}).count(),mode==='panel'?0:1);
 assert.equal(await page.getByRole('link',{name:'Acompanhar pedido'}).count(),mode==='whatsapp'?0:1);
 assert.equal(await page.locator('.cart-item').count(),mode==='whatsapp'?1:0);assert.equal(requests,1);
 assert.ok(page.url().endsWith('/menu?loja=1'));assert.equal(browser.contexts().length,1);
 }finally{await browser.close();}
});
