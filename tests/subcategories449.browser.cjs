const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {chromium}=require('playwright');
const root=path.resolve(__dirname,'..');
const css=fs.readFileSync(path.join(root,'static/subcategories261.css'),'utf8');
const js=fs.readFileSync(path.join(root,'static/subcategories261.js'),'utf8');
const fixture='<!doctype html><html><head><style>*{box-sizing:border-box}body{font:16px system-ui}.category-admin-row{display:grid;grid-template-columns:1fr 1fr;opacity:.35}.nu449-category-body{display:grid}.category-admin-row input{color:#eeeeee}'+css+'</style></head><body class="professional-area">'
+'<main class="pro-dashboard"><details id="categorias-loja" open><div class="category-admin-list">'
+'<div class="category-admin-row nu449-category-row"><details class="nu449-category-details" id="categoria-7">'
+'<summary class="nu449-category-header" aria-label="Abrir categoria Tabacaria e suas subcategorias"><span class="nu449-category-ident"><strong class="nu449-category-name">Tabacaria</strong><span class="nu449-category-meta">0 subcategorias</span></span><span class="nu449-category-chevron">⌄</span></summary>'
+'<div class="nu449-category-body" data-subcats-sector261="7"><div class="nu449-category-actions"><button type="button" class="btn primary nu449-add-button" data-subcats-add-toggle261 aria-expanded="false">＋ Adicionar subcategoria</button></div>'
+'<form class="nu-subcats261-add nu449-subcat-form" data-subcats-add-form261 hidden><label>Nome da nova subcategoria<input name="name" class="input" required placeholder="Ex.: Sedas"></label><button>Salvar</button></form>'
+'<details class="nu449-edit-category"><summary>Editar categoria</summary><form><input name="name" value="Tabacaria"></form></details></div></details></div>'
+'<div class="category-admin-row nu449-category-row"><details class="nu449-category-details" id="categoria-8"><summary class="nu449-category-header"><strong class="nu449-category-name">Bebidas não alcoólicas</strong><span class="nu449-category-chevron">⌄</span></summary><div class="nu449-category-body" data-subcats-sector261="8"><button type="button">＋ Adicionar subcategoria</button></div></details></div>'
+'</div></details></main></body></html>';
test('mobile category names readable and inline create optional',async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.NOWUP_CHROME_EXECUTABLE?{executablePath:process.env.NOWUP_CHROME_EXECUTABLE}:{})});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844}});
  await page.setContent(fixture);
  await page.addScriptTag({content:js});
  await page.evaluate(()=>document.dispatchEvent(new Event('DOMContentLoaded')));
  const name=page.locator('#categoria-7 .nu449-category-name');
  assert.equal(await name.isVisible(),true);
  const color=await name.evaluate(el=>getComputedStyle(el).color);
  assert.equal(color,'rgb(36, 19, 56)');
  assert.equal(await page.locator('#categoria-7 [data-subcats-add-toggle261]').isVisible(),false);
  assert.equal(await page.locator('#categoria-8 .nu449-category-name').isVisible(),true);
  await page.locator('#categoria-7 > summary').click();
  assert.equal(await page.locator('#categoria-7 [data-subcats-add-toggle261]').isVisible(),true);
  const form=page.locator('#categoria-7 [data-subcats-add-form261]');
  assert.equal(await form.isVisible(),false);
  await page.locator('#categoria-7 [data-subcats-add-toggle261]').click();
  assert.equal(await form.isVisible(),true);
  assert.equal(await page.locator('#categoria-7 [data-subcats-add-toggle261]').getAttribute('aria-expanded'),'true');
  assert.equal(await page.locator('#categoria-8 .nu449-category-body').isVisible(),false);
  await page.locator('#categoria-7 [data-subcats-add-toggle261]').click();
  assert.equal(await form.isVisible(),false);
 }finally{await browser.close();}
});
