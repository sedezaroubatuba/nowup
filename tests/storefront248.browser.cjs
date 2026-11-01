const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {chromium}=require('playwright');
const root=path.join(__dirname,'..');
const code=fs.readFileSync(path.join(root,'static/storefront232.js'),'utf8');
const css=fs.readFileSync(path.join(root,'static/storefront232.css'),'utf8');
const legacy=fs.readFileSync(path.join(root,'templates/menu.html'),'utf8').match(/html body\.public-profile-area\.nu187-store-home \.nu207-banners\{[^}]+\}/)[0];
const fixture=`<!doctype html><html><head><style>
*{box-sizing:border-box}body{margin:0} .nu187-intro{height:300px}.nu187-cover{height:240px}
.nu-menu-sticky{position:fixed!important;top:0!important;width:100%;background:white}
.nu83-catalog-heading{height:60px} .menu-category-nav{height:44px}
.nu207-banners{height:180px;background:purple}.nu190-showcase{height:2400px}
@media(min-width:901px){html body.public-profile-area.nu228-desktop-catalog [data-native-menu] .nu187-intro{display:block!important}}
</style></head><body class="public-profile-area nu187-store-home nu170-fixed-catalog"><main data-native-menu><div class="container">
<section class="nu187-intro"><div class="nu187-cover"></div></section>
<div class="nu-menu-sticky"><div class="nu83-catalog-heading"><input aria-label="Pesquisar produtos"></div><nav class="menu-category-nav">Categorias</nav></div>
<section class="nu207-banners">Promoções da loja</section><div class="nu190-showcase">Produtos</div>
</div></main></body></html>`;
async function setup(width){
 const executablePath=process.env.NOWUP_CHROME_EXECUTABLE;
 const browser=await chromium.launch({headless:true,...(executablePath?{executablePath}:{})});const page=await browser.newPage({viewport:{width,height:850}});
 await page.route('http://nowup.local/**',r=>r.fulfill({contentType:'text/html',body:fixture}));await page.goto('http://nowup.local/p/loja');
 await page.addStyleTag({content:css});await page.addStyleTag({content:legacy});await page.addScriptTag({content:code});await page.evaluate(()=>document.dispatchEvent(new Event('DOMContentLoaded')));
 await page.waitForFunction(()=>document.body.classList.contains('nu233-store'));
 return {browser,page};
}
test('desktop banner scrolls below sticky search and disappears in product search',async()=>{
 const {browser,page}=await setup(1440);try{
  const banner=page.locator('.nu207-banners');await banner.waitFor({state:'visible'});
  assert.ok((await banner.boundingBox()).width>750);
  assert.equal(await page.locator('.nu-menu-sticky').evaluate(e=>getComputedStyle(e).position),'sticky');
  await page.evaluate(()=>window.scrollTo(0,850));await page.waitForFunction(()=>document.querySelector('.nu207-banners').getBoundingClientRect().bottom<0);

  await page.evaluate(()=>{document.body.classList.remove('nu187-store-home');document.body.classList.add('nu228-desktop-catalog');});
  await page.waitForFunction(()=>getComputedStyle(document.querySelector('.nu187-intro')).display==='none');
  await page.addStyleTag({content:'@media(min-width:901px){html body.public-profile-area.nu228-desktop-catalog [data-native-menu] .nu-menu-sticky{position:sticky!important;top:0!important}html body.public-profile-area.nu228-desktop-catalog [data-native-menu] .nu207-banners{display:block!important}}'});
  assert.equal(await page.locator('.nu-menu-sticky').evaluate(e=>getComputedStyle(e).position),'sticky');
  assert.equal(await banner.isVisible(),false);
 }finally{await browser.close();}
});
test('mobile slideshow scrolls away while search and categories remain usable',async()=>{
 const {browser,page}=await setup(390);try{
  const banner=page.locator('.nu207-banners');await banner.waitFor({state:'visible'});
  assert.equal(await banner.evaluate(e=>!!e.parentElement.closest('[data-native-menu]')&&!e.parentElement.classList.contains('nu-menu-sticky')),true);
  const before=await banner.boundingBox();assert.ok(before.y>=(await page.locator('.nu-menu-sticky').boundingBox()).y);assert.equal(await banner.evaluate(e=>e.previousElementSibling.classList.contains('nu-menu-sticky')),true);
  await page.evaluate(()=>window.scrollTo(0,600));
  await page.waitForFunction(()=>document.querySelector('.nu207-banners').getBoundingClientRect().bottom<0);
  const after=await banner.boundingBox();assert.ok(after.y<before.y-500);
  assert.equal(await page.locator('.menu-category-nav').isVisible(),true);
  assert.ok(Math.abs((await page.locator('.nu-menu-sticky').boundingBox()).y)<2);
  await page.evaluate(()=>document.body.classList.remove('nu187-store-home'));
  await banner.waitFor({state:'hidden'});
 }finally{await browser.close();}
});

test('late slideshow is placed below search and returns there after category navigation',async()=>{
 const {browser,page}=await setup(390);try{
  await page.evaluate(()=>{const banner=document.querySelector('.nu207-banners');document.querySelector('.nu187-intro').before(banner);window.dispatchEvent(new Event('nowup-slide-ready286'));});
  await page.waitForFunction(()=>document.querySelector('.nu-menu-sticky').nextElementSibling?.classList.contains('nu207-banners'));
  await page.evaluate(()=>window.scrollTo(0,650));
  await page.waitForFunction(()=>Math.abs(document.querySelector('.nu-menu-sticky').getBoundingClientRect().top)<2);
  assert.ok((await page.locator('.nu207-banners').boundingBox()).y<0);
  await page.evaluate(()=>{document.body.classList.remove('nu187-store-home');});await page.locator('.nu207-banners').waitFor({state:'hidden'});
  await page.evaluate(()=>{document.body.classList.add('nu187-store-home');window.scrollTo(0,0);});
  await page.waitForFunction(()=>document.querySelector('.nu207-banners').previousElementSibling?.classList.contains('nu-menu-sticky'));
  await page.evaluate(async()=>{await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));window.scrollTo(0,0);});
  await page.waitForFunction(()=>{const search=document.querySelector('.nu-menu-sticky').getBoundingClientRect(),banner=document.querySelector('.nu207-banners').getBoundingClientRect();return window.scrollY===0&&banner.top>=search.bottom;});
  const search=await page.locator('.nu-menu-sticky').boundingBox(),banner=await page.locator('.nu207-banners').boundingBox();assert.ok(banner.y>=search.y+search.height);
 }finally{await browser.close();}
});


test('wide slideshow keeps its height with a square lazy-loading placeholder',async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.NOWUP_CHROME_EXECUTABLE?{executablePath:process.env.NOWUP_CHROME_EXECUTABLE}:{})});
 try{for(const width of [390,1440]){
  const page=await browser.newPage({viewport:{width,height:850}});
  const square='data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="480" height="480"%3E%3C/svg%3E';
  const wide='data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="800" height="300"%3E%3C/svg%3E';
  await page.setContent(`<style>*{box-sizing:border-box}body{margin:0}.nu207-track{display:flex}.nu207-card{flex:0 0 100%;background:#f5f1fa}.nu207-card img{width:100%;height:auto}${css}</style><body class="public-profile-area nu233-store nu187-store-home ${width<901?'nu232-store':'nu233-desktop'}"><main data-native-menu><section class="nu207-banners"><div class="nu207-track"><button class="nu207-card"><img src='${wide}'></button><button class="nu207-card"><img src='${square}'></button></div><div class="nu207-controls">‹ · · ›</div></section></main>`);
  const frame=await page.locator('.nu207-track').boundingBox();assert.ok(Math.abs(frame.height-frame.width*3/8)<2,JSON.stringify(frame));
  const image=await page.locator('.nu207-card img').first().boundingBox();assert.ok(Math.abs(image.height-frame.height)<2,JSON.stringify({image,frame}));
  await page.close();
 }}finally{await browser.close();}
});


test('idle store stays settled and scrolling does not remeasure the whole layout',async()=>{
 const {browser,page}=await setup(390);try{
  await page.waitForTimeout(250);
  await page.evaluate(()=>{window.measures306=0;const bar=document.querySelector('.nu-menu-sticky'),rect=bar.getBoundingClientRect.bind(bar);bar.getBoundingClientRect=()=>{window.measures306++;return rect();};});
  await page.waitForTimeout(160);assert.equal(await page.evaluate(()=>window.measures306),0);
  await page.evaluate(()=>{for(let i=0;i<30;i++){window.dispatchEvent(new Event('scroll'));const row=document.createElement('span');row.textContent='Quantidade '+i;document.querySelector('.nu190-showcase').append(row);}document.body.classList.add('nu143-has-cart');});
  await page.waitForTimeout(160);assert.equal(await page.evaluate(()=>window.measures306),0);
  await page.evaluate(()=>{document.querySelector('.nu83-catalog-heading').style.height='80px';});
  await page.waitForFunction(()=>parseInt(document.body.style.getPropertyValue('--nu232-sticky-height'),10)===Math.ceil(document.querySelector('.nu-menu-sticky').getBoundingClientRect().height));
  assert.ok(await page.evaluate(()=>window.measures306)>0);
 }finally{await browser.close();}
});

test('highlight photos are processed only near the screen and outside load handlers',async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.NOWUP_CHROME_EXECUTABLE?{executablePath:process.env.NOWUP_CHROME_EXECUTABLE}:{})});try{
 const page=await browser.newPage({viewport:{width:390,height:850}});
 await page.setContent('<div style="height:2000px"></div><article class="nu256-highlight"><img width="100" height="100"></article>');
 await page.evaluate(()=>{window.reads306=0;window.callbacks306=[];window.requestIdleCallback=fn=>{window.callbacks306.push(fn);};const original=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(...a){const c=original.apply(this,a),read=c.getImageData.bind(c);c.getImageData=(...v)=>{window.reads306++;return read(...v);};return c;};const c=document.createElement('canvas');c.width=c.height=100;const ctx=c.getContext('2d');ctx.fillStyle='white';ctx.fillRect(0,0,100,100);ctx.fillStyle='purple';ctx.fillRect(30,30,40,40);window.photo306=c.toDataURL();});
 await page.addScriptTag({content:fs.readFileSync(path.join(root,'static/offer-photos274.js'),'utf8')});
 await page.evaluate(()=>{document.querySelector('img').src=window.photo306;});
 await page.waitForTimeout(150);assert.equal(await page.evaluate(()=>window.reads306),0);assert.equal(await page.evaluate(()=>window.callbacks306.length),0);
 await page.locator('img').scrollIntoViewIfNeeded();await page.waitForFunction(()=>window.callbacks306.length>0);assert.equal(await page.evaluate(()=>window.reads306),0);
 }finally{await browser.close();}
});
