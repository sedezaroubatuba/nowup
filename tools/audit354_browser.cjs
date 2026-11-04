/* Real UI audit against tools/audit354_run.py only: never sends WhatsApp messages. */
const fs=require('fs'),path=require('path'),{execFileSync}=require('child_process'),{chromium,devices}=require('playwright');
const manifest=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),base=manifest.base;
if(!/^http:\/\/127\.0\.0\.1:\d+$/.test(base))throw Error('Loopback audit server required');
const run=manifest.run_dir,results=[],stamp=Date.now();
const py=process.env.AUDIT_PYTHON||'python3';
function row(query,args){return JSON.parse(execFileSync(py,['-c','import sqlite3,json,sys;c=sqlite3.connect(sys.argv[1]);c.row_factory=sqlite3.Row;r=c.execute(sys.argv[2],json.loads(sys.argv[3])).fetchone();print(json.dumps(dict(r) if r else None))',path.join(run,'audit.db'),query,JSON.stringify(args)],{encoding:'utf8'}));}
function record(name,ok,detail=''){results.push({name,ok,detail});console.log(name,ok,String(detail).slice(0,200));}
const profiles=[['Android 360x800',{viewport:{width:360,height:800},isMobile:true,hasTouch:true,deviceScaleFactor:2}],['Galaxy S9+',devices['Galaxy S9+']],['Pixel 7',devices['Pixel 7']],['iPhone SE viewport',devices['iPhone SE']],['iPhone 13 viewport',devices['iPhone 13']],['iPhone 13 Pro Max viewport',devices['iPhone 13 Pro Max']],['Desktop 1366',{viewport:{width:1366,height:768}}],['Desktop 1920',{viewport:{width:1920,height:1080}}]];
(async()=>{const browser=await chromium.launch({headless:true});
try{
 if(!process.env.NOWUP_AUDIT_ONE){
 const mixedStart=performance.now();
 const merchantWrites=manifest.stores.map((s,i)=>(async()=>{const body=new FormData();for(const [k,v] of Object.entries({name:'Produto misto354 '+stamp+' '+i,price:'3,50',category:'Bebidas',available:'1',extras_mode:'none'}))body.append(k,v);body.append('photo',new Blob([fs.readFileSync(path.join(run,'uploads',s.photo))],{type:'image/jpeg'}),'foto.jpg');const r=await fetch(base+'/painel/cardapio/produtos',{method:'POST',headers:{Origin:base,Cookie:'nowup_session='+s.merchant_token},body,redirect:'manual'});return {kind:'merchant-photo',status:r.status,ok:r.status===303};})());
 const simultaneousOrders=manifest.customers.map((u,i)=>(async()=>{const body=new URLSearchParams({customer_name:'Cliente teste',customer_phone:'12988888888',cart_json:JSON.stringify([{id:u.product,quantity:1}]),fulfillment_type:'pickup',payment_method:'pix',request_key:'mixed354-'+stamp+'-'+i});const r=await fetch(base+'/p/'+u.slug+'/menu/whatsapp',{method:'POST',headers:{Origin:base,Cookie:'nowup_loja345_'+u.store+'='+u.token},body});let d={};try{d=await r.json();}catch{}return {kind:'whatsapp',status:r.status,ok:r.status===200&&d.prepared&&!d.recorded&&d.total_cents===1250};})());
 const mixed=await Promise.all([...merchantWrites,...simultaneousOrders]);
 record('50 merchant photo uploads plus 100 WhatsApp checkouts',mixed.every(r=>r.ok),JSON.stringify({elapsed_ms:Math.round(performance.now()-mixedStart),success:mixed.filter(r=>r.ok).length,total:mixed.length,errors:mixed.filter(r=>!r.ok)}));
 }
 for(let i=0;i<(process.env.NOWUP_AUDIT_ONE?'1':profiles.length);i++){
  const [label,options]=profiles[i],store=manifest.stores[i],ctx=await browser.newContext({...options,serviceWorkers:'block'}),page=await ctx.newPage(),errors=[],httpErrors=[];
  page.setDefaultTimeout(12000);page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=500)httpErrors.push([r.status(),r.url()]);});
  // External navigation is forbidden: inspect the prepared link only.
  await page.route('https://wa.me/**',r=>r.abort());await page.route('https://api.whatsapp.com/**',r=>r.abort());
  const email=`browser354-${stamp}-${i}@example.com`;
  try{
   await page.goto(base+'/p/'+store.slug+'/cadastro');
   const form=page.locator('form.nu205-form');
   for(const [key,value] of Object.entries({name:'Cliente teste '+i,email,phone:'12988888888',address:'Rua teste 123',neighborhood:'Centro',city:'São Sebastião',password:'Browser354-password',password_confirm:'Browser354-password'}))await form.locator('[name='+key+']').fill(value);
   await form.locator('[name=state]').selectOption('SP');await form.locator('[name=accept_terms]').check();
   await Promise.all([page.waitForURL('**/aguardando*'),form.getByRole('button',{name:'Cadastrar e confirmar e-mail'}).click()]);
   const user=row('SELECT * FROM users WHERE customer_email345=? AND customer_store345=?',[email,store.id]);
   record(label+' customer signup',!!user&&user.email_verified===0,page.url());
   await page.goto(base+'/p/'+store.slug+'/verificar-email?token='+encodeURIComponent(user.verification_token));
   await page.locator('#nowup-login-form349 [name=email]').fill(email);await page.locator('#nowup-login-form349 [name=password]').fill('Browser354-password');
   await page.locator('.password-toggle').click();record(label+' show password',await page.locator('[name=password]').getAttribute('type')==='text');
   await Promise.all([page.waitForURL('**/menu?loja=1'),page.locator('#nowup-login-confirm349').click()]);
   record(label+' store login',(await ctx.cookies()).some(c=>c.name==='nowup_loja345_'+store.id));
   // Assert layout before searching or opening a dialog.
   record(label+' header name and actions do not overlap',await page.evaluate(()=>{const a=document.querySelector('.storeapp-brand256').getBoundingClientRect(),b=document.querySelector('.storeapp-actions256').getBoundingClientRect();return a.bottom<=b.top+1||a.right<=b.left+1;}));
   record(label+' no horizontal page overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2),await page.evaluate(()=>`${document.documentElement.scrollWidth}/${innerWidth}`));
   const cookie=page.getByRole('button',{name:'Entendi',exact:true});if(await cookie.isVisible())await cookie.click();
   const source=page.locator('[data-source256]');await source.first().getByRole('button',{name:/Adicionar|Personalizar/}).first().click();
   if(await source.first().locator('.nu190-add').isVisible())await source.first().locator('.nu190-add').click();
   const dish=page.locator('.nu151-dish-dialog[open]');if(await dish.count())await dish.locator('[data-add]').click();
   await page.locator('[data-cart-summary]').click();
   record(label+' cart content visible',await page.getByRole('heading',{name:'Seu carrinho',exact:true}).isVisible());
   await page.locator('[data-checkout]').click();
   const checkoutVisible=await page.getByRole('heading',{name:'Finalizar pedido',exact:true}).isVisible();record(label+' checkout content visible',checkoutVisible);
   if(!checkoutVisible){fs.writeFileSync(path.join(run,'checkout-diagnostic-'+i+'.json'),JSON.stringify(await page.evaluate(()=>[...document.querySelectorAll('dialog')].map(d=>({class:d.className,open:d.open,rect:d.getBoundingClientRect().toJSON(),html:d.innerHTML.slice(0,800),children:[...d.children].map(c=>({tag:c.tagName,class:c.className,hidden:c.hidden,display:getComputedStyle(c).display,visibility:getComputedStyle(c).visibility,rect:c.getBoundingClientRect().toJSON()}))}))),null,2));throw Error('Checkout content is invisible; DOM diagnostic saved');}
   const checkout=page.locator('[data-checkout-dialog] form');
   await checkout.locator('[name=fulfillment_type]').selectOption('pickup');await checkout.locator('[name=payment_method]').selectOption('pix');
   await checkout.locator('button[type=submit],button.btn.primary').last().click();
   await page.locator('[data-whatsapp-ready257]').waitFor();const whatsapp=page.getByRole('link',{name:'Abrir WhatsApp e enviar'});
   record(label+' prepared WhatsApp link',(await whatsapp.getAttribute('href')).startsWith('https://wa.me/5512999999999?text='));
   record(label+' WhatsApp not falsely recorded',await page.getByRole('link',{name:'Acompanhar pedido',exact:true}).count()===0);
   await page.locator('[data-dialog-close]').click();
   const search=page.locator('[data-product-search]');await search.fill('NOME_INEXISTENTE_354');await search.dispatchEvent('input');
   record(label+' search absent product',await page.locator('.nu190-card:visible').count()===0,await page.locator('.nu190-card:visible').count());
   fs.writeFileSync(path.join(run,'search-diagnostic-'+i+'.json'),JSON.stringify(await page.evaluate(()=>({query:document.querySelector('[data-product-search]').value,body:document.body.className,showcases:[...document.querySelectorAll('.nu190-showcase,.nu191-category-view')].map(d=>({class:d.className,hidden:d.hidden,display:getComputedStyle(d).display})),products:[...document.querySelectorAll('[data-product]')].slice(0,3).map(d=>({hidden:d.hidden,display:getComputedStyle(d).display,name:d.dataset.name}))})),null,2));
   await search.fill('Produto');await search.dispatchEvent('input');record(label+' search matching product',await page.locator('[data-product]:visible,.nu190-card:visible').count()>0);
   // Only internal inspection of screenshots with synthetic customers.
   await page.screenshot({path:path.join(run,'ui-'+i+'.png'),fullPage:false});
   record(label+' no JS exceptions',errors.length===0,errors.join('; '));record(label+' no HTTP 5xx',httpErrors.length===0,JSON.stringify(httpErrors));
  }catch(e){record(label+' flow completed',false,e.stack);await page.screenshot({path:path.join(run,'failure-'+i+'.png')});}
  finally{await ctx.close();}
 }
 // A merchant uses the real product and photo upload form on a small phone.
 const s=manifest.stores[0],ctx=await browser.newContext({viewport:{width:390,height:844},hasTouch:true,isMobile:true}),page=await ctx.newPage();page.setDefaultTimeout(12000);
 await ctx.addCookies([{name:'nowup_session',value:s.merchant_token,url:base}]);
 try{
  await page.goto(base+'/painel#cardapio-independente');record('Merchant WhatsApp settings visible',await page.locator('form[action="/painel/cardapio/whatsapp"]').isVisible());
  await page.goto(base+'/painel#novo-produto');if(!await page.locator('#novo-produto').evaluate(d=>d.open))await page.locator('#novo-produto > summary').click();const form=page.locator('#novo-produto > form');
  await form.locator('[name=name]').fill('Produto via celular354 '+stamp);await form.locator('[name=price]').fill('19,90');
  await form.locator('[name=photo]').setInputFiles(path.join(run,'uploads',s.photo));
  await page.locator('.image-editor[open] [data-ie-apply]').click();await page.locator('.image-editor[open]').waitFor({state:'hidden'});
  const cookie=page.getByRole('button',{name:'Entendi',exact:true});if(await cookie.isVisible())await cookie.click();
  const submit=form.locator('button[type=submit],button.btn.primary').last();await Promise.all([page.waitForURL('**/painel?ok=produto*'),submit.click()]);
  const product=row('SELECT * FROM products WHERE professional_id=? AND name=?',[s.id,'Produto via celular354 '+stamp]);record('Merchant phone product and photo registration',!!product&&!!product.image_filename);
  await page.goto(base+'/painel#ingredientes320');const ingName='Ingrediente foto354 '+stamp;const ingForm=page.locator('#ingredientes320 > form').first();
  await ingForm.locator('[name=name]').fill(ingName);await ingForm.locator('[name=price]').fill('2,00');await ingForm.locator('[name=photo]').setInputFiles(path.join(run,'uploads',s.photo));await page.locator('.image-editor[open] [data-ie-apply]').click();await page.locator('.image-editor[open]').waitFor({state:'hidden'});
  await Promise.all([page.waitForURL('**/painel?ok=ingrediente*'),ingForm.getByRole('button',{name:'Salvar item',exact:true}).click()]);
  const ingredient=row('SELECT * FROM ingredients320 WHERE professional_id=? AND name=?',[s.id,ingName]);record('Merchant ingredient photo registered',!!ingredient?.image_filename);
  await page.goto(base+'/painel#novo-lanche322');const meal=page.locator('#novo-lanche322 > form');await meal.locator('[name=name]').fill('Lanche importado354 '+stamp);await meal.locator('[name=price]').fill('25,00');
  const ingredientSearch=meal.getByRole('searchbox',{name:'Buscar ingrediente cadastrado'});if(!await ingredientSearch.isVisible())await meal.getByText('Importar itens cadastrados',{exact:true}).click();
  await ingredientSearch.fill(ingName);await meal.getByRole('button',{name:'+ '+ingName,exact:true}).click();
  record('Ingredient imported with its photo',await meal.locator('.nu192-row img[src="/uploads/'+ingredient.image_filename+'"]').count()>0);
  await Promise.all([page.waitForURL('**/painel?ok=refeicao*'),meal.getByRole('button',{name:'Salvar lanche ou refeição',exact:true}).click()]);
  const mealRecord=row('SELECT customization192 FROM products WHERE professional_id=? AND name=?',[s.id,'Lanche importado354 '+stamp]);record('Imported ingredient saved in meal',!!mealRecord&&JSON.parse(mealRecord.customization192).ingredients.some(i=>i.ingredient_id320===ingredient.id&&i.image_filename===ingredient.image_filename));
  await page.goto(base+'/painel#relatorios');record('Merchant reports section visible',await page.locator('#relatorios').isVisible());
  await page.goto(base+'/painel/vendas-manuais/relatorios');record('Consolidated report HTTP',await page.locator('body').innerText().then(t=>!t.includes('Não encontrada')));
 }catch(e){record('Merchant phone flow',false,e.stack);await page.screenshot({path:path.join(run,'merchant-failure.png')});}finally{await ctx.close();}
}finally{await browser.close();fs.writeFileSync(path.join(run,process.env.NOWUP_AUDIT_RESULT_FILE||'browser-results.json'),JSON.stringify({engine:'Chromium; device profiles are emulations, not physical or Safari tests',results},null,2));}
})();
