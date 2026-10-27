const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {chromium}=require('playwright');
const root=path.join(__dirname,'..');
const code=fs.readFileSync(path.join(root,'static/storefront232.js'),'utf8');
const css=fs.readFileSync(path.join(root,'static/storefront232.css'),'utf8');
const fixture=`<!doctype html><html><head><style>
*{box-sizing:border-box}body{margin:0} .nu187-intro{height:300px}.nu187-cover{height:240px}
.nu-menu-sticky{position:fixed!important;top:0!important;width:100%;background:white}
.nu83-catalog-heading{height:60px} .menu-category-nav{height:44px}
.nu207-banners{height:180px;background:purple}.nu190-showcase{height:2400px}
@media(min-width:901px){html body.public-profile-area.nu228-desktop-catalog [data-native-menu] .nu187-intro{display:block!important}}
</style></head><body class="public-profile-area nu187-store-home nu170-fixed-catalog"><main data-native-menu>
<section class="nu187-intro"><div class="nu187-cover"></div></section>
<div class="nu-menu-sticky"><div class="nu83-catalog-heading"><input aria-label="Pesquisar produtos"></div><nav class="menu-category-nav">Categorias</nav></div>
<section class="nu207-banners">Promoções da loja</section><div class="nu190-showcase">Produtos</div>
</main></body></html>`;
async function setup(width){
 const executablePath=process.env.NOWUP_CHROME_EXECUTABLE;
 const browser=await chromium.launch({headless:true,...(executablePath?{executablePath}:{})});const page=await browser.newPage({viewport:{width,height:850}});
 await page.route('http://nowup.local/**',r=>r.fulfill({contentType:'text/html',body:fixture}));await page.goto('http://nowup.local/p/loja');
 await page.addStyleTag({content:css});await page.addScriptTag({content:code});await page.evaluate(()=>document.dispatchEvent(new Event('DOMContentLoaded')));
 await page.waitForFunction(()=>document.body.classList.contains('nu233-store'));
 return {browser,page};
}
test('desktop banner is wide, scrolls away with search, and disappears in product search',async()=>{
 const {browser,page}=await setup(1440);try{
  const banner=page.locator('.nu207-banners');await banner.waitFor({state:'visible'});
  assert.ok((await banner.boundingBox()).width>750);
  assert.equal(await page.locator('.nu-menu-sticky').evaluate(e=>getComputedStyle(e).position),'relative');
  await page.evaluate(()=>window.scrollTo(0,850));await page.waitForFunction(()=>document.querySelector('.nu-menu-sticky').getBoundingClientRect().bottom<0);
  assert.equal(await page.locator('.nu248-slide-toggle').isVisible(),false);
  await page.evaluate(()=>{document.body.classList.remove('nu187-store-home');document.body.classList.add('nu228-desktop-catalog');});
  await page.waitForFunction(()=>getComputedStyle(document.querySelector('.nu187-intro')).display==='none');
  await page.addStyleTag({content:'@media(min-width:901px){html body.public-profile-area.nu228-desktop-catalog [data-native-menu] .nu-menu-sticky{position:sticky!important;top:0!important}}'});
  assert.equal(await page.locator('.nu-menu-sticky').evaluate(e=>getComputedStyle(e).position),'relative');
 }finally{await browser.close();}
});
test('mobile sticky banner can be collapsed and reopened without losing categories',async()=>{
 const {browser,page}=await setup(390);try{
  await page.evaluate(()=>window.scrollTo(0,320));const toggle=page.getByRole('button',{name:'Subir slide ↑'});await toggle.waitFor({state:'visible'});
  const before=await page.locator('.nu-menu-sticky').boundingBox();assert.ok(Math.abs(before.y)<2);
  await toggle.click();await page.locator('.nu207-banners').waitFor({state:'hidden'});
  assert.equal(await page.locator('.menu-category-nav').isVisible(),true);
  assert.equal(await page.getByRole('button',{name:'Mostrar slide ↓'}).getAttribute('aria-expanded'),'false');
  assert.ok((await page.locator('.nu-menu-sticky').boundingBox()).height<before.height);
  await page.getByRole('button',{name:'Mostrar slide ↓'}).click();await page.locator('.nu207-banners').waitFor({state:'visible'});
  await page.setViewportSize({width:1440,height:850});await page.waitForFunction(()=>document.body.classList.contains('nu233-desktop'));
  assert.equal(await page.locator('.nu248-slide-toggle').isVisible(),false);
 }finally{await browser.close();}
});
