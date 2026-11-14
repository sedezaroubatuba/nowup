const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),{JSDOM,VirtualConsole}=require('jsdom');
const fixture=fs.readFileSync('tests/storeapp257.browser.cjs','utf8').match(/const fixture=`([\s\S]*?)`;/)[1];
test('cardapio keeps checkout in NowUp, clears cart after confirmation, never opens WhatsApp',async()=>{
 const dom=new JSDOM(fixture,{url:'https://nowup.local/p/shop/cardapio',runScripts:'outside-only',virtualConsole:new VirtualConsole()}),w=dom.window;let opens=0;
 w.NOWUP_MENU={customerId:10,open:true,whatsappCheckout:true};w.open=()=>opens++;
 w.fetch=async()=>({ok:true,headers:{get:()=> 'application/json'},json:async()=>({prepared:true,recorded:true,confirmed:true,internal_checkout432:true,path:'/p/shop',redirect:'/p/shop/pedido/abc123',whatsapp_url:'https://wa.me/5512999999999?text=Pedido'})});
 const key='nowup-cart:whatsapp257:u:10:/p/shop';w.localStorage.setItem(key,JSON.stringify([['1',{productId:1,name:'Produto',unitPrice:300,quantity:2,options:[],max:99}]]));w.eval(fs.readFileSync('static/menu88.js','utf8'));w.document.querySelector('form').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await new Promise(r=>setImmediate(r));
 assert.equal(opens,0);assert.equal(w.document.querySelector('[data-whatsapp-ready257]'),null);assert.deepEqual(JSON.parse(w.localStorage.getItem(key)||'[]'),[]);assert.match(w.document.querySelector('[data-checkout-feedback251]').textContent,/Pedido enviado com sucesso/);w.close();
});
