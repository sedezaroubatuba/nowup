const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {chromium}=require('playwright');
const file=name=>fs.readFileSync(path.join(__dirname,'..',name),'utf8');
const html='<!doctype html><html><head><meta charset="utf-8"></head><body><main data-native-menu>'
+'<details open data-product data-group260="1" data-id="10" data-name="Balas Fini" data-price="550"><summary>Balas Fini</summary>'
+'<article data-product data-id="11" data-name="Balas Fini — Morango" data-price="550" data-max="99" data-category="doces" data-group-photo260="/uploads/capa-fini.jpg">'
+'<label><input type="number" data-product-quantity value="1"></label><button data-add>Adicionar Morango</button></article>'
+'<article data-product data-id="12" data-name="Balas Fini — Uva" data-price="620" data-max="99" data-category="doces" data-group-photo260="/uploads/uva-fini.jpg">'
+'<label><input type="number" data-product-quantity value="1"></label><button data-add>Adicionar Uva</button></article>'
+'</details><aside class="menu-cart"><div data-cart-items></div><b data-cart-total></b><button data-checkout>Continuar</button></aside>'
+'<dialog data-checkout-dialog><form action="/p/example/menu/pedido" method="post">'
+'<input name="customer_name" value="Cliente"><input name="cart_json" data-cart-json>'
+'<select name="fulfillment_type" data-fulfillment><option value="pickup">Retirada</option></select>'
+'<select name="payment_method" data-payment><option value="pix">Pix</option></select>'
+'<b data-dialog-total></b><button type="submit">Finalizar</button></form></dialog>'
+'</main></body></html>';
test('grouped cart uses the matching item photo, or universal cover, with flavor name',async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.NOWUP_CHROME_EXECUTABLE?{executablePath:process.env.NOWUP_CHROME_EXECUTABLE}:{})});
 try{
  const page=await browser.newPage();
  await page.route('https://nowup.local/**',route=>route.fulfill({contentType:'text/html',body:html}));
  await page.goto('https://nowup.local/p/example/menu');
  await page.evaluate(()=>{window.NOWUP_MENU={customerId:18,open:true,minimumOrder:0};});
  await page.addScriptTag({content:file('static/menu88.js')});
  await page.locator('[data-id="11"] [data-add]').click();
  await page.locator('[data-id="12"] [data-add]').click();
  const cart=page.locator('[data-cart-items] .cart-item');
  assert.equal(await cart.count(),2);
  assert.match(await cart.nth(0).innerText(),/Balas Fini — Morango/);
  assert.match(await cart.nth(1).innerText(),/Balas Fini — Uva/);
  assert.equal(await cart.nth(0).locator('img.nu260-cart-cover').getAttribute('src'),'/uploads/capa-fini.jpg');
  assert.equal(await cart.nth(1).locator('img.nu260-cart-cover').getAttribute('src'),'/uploads/uva-fini.jpg');
  assert.equal((await page.locator('[data-cart-total]').textContent()).trim(),'R$\u00a011,70');
  const payload=await page.locator('[data-cart-json]').inputValue();
  const items=JSON.parse(payload);
  assert.deepEqual(items.map(x=>x.id),[11,12]);
  assert.deepEqual(items.map(x=>x.quantity),[1,1]);
 }finally{await browser.close();}
});
