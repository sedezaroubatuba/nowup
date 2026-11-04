const test=require('node:test'),assert=require('node:assert/strict'),fs=require('fs'),path=require('path'),{chromium}=require('playwright');
const read=p=>fs.readFileSync(path.join(__dirname,'..',p),'utf8');
test('mobile cart and checkout retain visible content after catalogue sections are hidden',async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844}});
  await page.route('https://nowup.local/**',r=>r.fulfill({contentType:'text/html',body:'<html></html>'}));
  await page.goto('https://nowup.local/p/shop/menu');
  await page.setContent(`<html><body class="public-profile-area"><script id="store-app256" type="application/json">{"slug":"shop"}</script><section class="native-menu" data-native-menu><div class="menu-layout" style="display:none"><dialog class="nu143-cart-dialog" data-cart-dialog143><aside class="menu-cart"><div class="panel"><header><h2>Seu carrinho</h2><button data-cart-close143>Fechar</button></header><div data-cart-items></div><b data-cart-total></b><b data-cart-subtotal143></b><b data-cart-fee143></b><button data-checkout>Continuar pedido</button></div></aside></dialog><dialog class="checkout-dialog" data-checkout-dialog><form data-order-form action="/p/shop/menu/whatsapp" method="post"><h2>Finalizar pedido</h2><button type="button" data-dialog-close>Fechar</button><input name="customer_name"><input data-cart-json><b data-dialog-total></b><select data-fulfillment><option value="pickup">Retirar</option></select><select data-payment><option value="pix">Pix</option></select></form></dialog></div><footer class="nu83-cart-dock"><button data-cart-summary>Ver carrinho<strong><span data-dock-total></span></strong></button></footer></section></body></html>`);
  await page.addStyleTag({content:'.menu-cart>.panel,dialog>form{display:none!important}'+read('static/cart144.css')});
  await page.addScriptTag({content:read('static/internal-contact106.js')});
  await page.addScriptTag({content:'window.NOWUP_MENU={open:true,customerId:1};'+read('static/menu88.js')});
  await page.addScriptTag({content:read('static/cart144.js')});
  // Populate a line as if restored from the customer's saved cart.
  await page.evaluate(()=>{document.querySelector('[data-cart-items]').innerHTML='<div class="cart-item"><b>Produto salvo</b></div>';document.querySelector('[data-checkout]').disabled=false;});
  await page.locator('[data-cart-summary]').click();
  assert(await page.getByText('Produto salvo',{exact:true}).isVisible());
  assert(await page.getByRole('heading',{name:'Seu carrinho'}).isVisible());
  await page.locator('[data-checkout]').click();
  assert(await page.getByRole('heading',{name:'Finalizar pedido'}).isVisible());
  assert(await page.locator('[name=customer_name]').isVisible());
  await page.locator('[data-order-form]').evaluate(f=>{const a=document.createElement('a');a.href='https://wa.me/5512999999999?text=teste';a.textContent='Abrir WhatsApp e enviar';f.append(a);});
  await page.waitForTimeout(30);assert(await page.getByRole('link',{name:'Abrir WhatsApp e enviar'}).isVisible());
  assert.equal(await page.locator('dialog[open]').count(),1);
  assert(await page.locator('[data-checkout-dialog]').evaluate(d=>d.parentElement.matches('[data-native-menu]')));
  await page.locator('[data-dialog-close]').click();assert.equal(await page.locator('dialog[open]').count(),0);
 }finally{await browser.close();}
});
