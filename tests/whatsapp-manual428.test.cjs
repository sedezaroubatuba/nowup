const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),{JSDOM}=require('jsdom');
const fixture=fs.readFileSync('tests/storeapp257.browser.cjs','utf8').match(/const fixture=`([\s\S]*?)`;/)[1];
for(const blocked of [true,false])test('WhatsApp manual handoff, popup blocked='+blocked,async()=>{
 const dom=new JSDOM(fixture,{url:'https://nowup.local/p/shop/cardapio',runScripts:'outside-only'}),w=dom.window;let destination='',attached=0;
 w.NOWUP_MENU={customerId:10,open:true,whatsappCheckout:true};w.HTMLElement.prototype.scrollIntoView=()=>{};
 w.open=()=>blocked?null:{closed:false,document:{body:{}},location:{replace:url=>destination=url},close(){}};
 w.NOWUP_PIX={attach:()=>attached++};w.fetch=async()=>({ok:true,headers:{get:()=> 'application/json'},json:async()=>({prepared:true,recorded:true,order_code:'NU-1',payment_method:'pix',redirect:'/p/shop/pedido/token257',whatsapp_url:'https://wa.me/5512999999999?text=Pedido',pix:{payload:'old-server'}})});
 const key='nowup-cart:whatsapp257:u:10:/p/shop';w.localStorage.setItem(key,JSON.stringify([['1',{productId:1,name:'Produto',unitPrice:300,quantity:2,options:[],max:99}]]));
 w.eval(fs.readFileSync('static/menu88.js','utf8'));w.document.querySelector('form').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));
 await new Promise(resolve=>setImmediate(resolve));
 const ready=w.document.querySelector('[data-whatsapp-ready257]');assert.ok(ready);assert.equal(ready.querySelectorAll('a').length,1);assert.match(ready.textContent,/Você não precisa voltar ao link/);assert.equal(attached,0);assert.equal(w.location.pathname,'/p/shop/cardapio');assert.deepEqual(JSON.parse(w.localStorage.getItem(key)||'[]'),[]);if(!blocked)assert.match(destination,/^https:\/\/wa.me\//);dom.window.close();
});
