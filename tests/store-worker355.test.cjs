const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
function worker(){
  const handlers={},opened=[],notices=[];
  const context={STORE_SCOPE:'/p/shop/',STORE_NAME:'Shop',URL,Response,
    self:{location:{origin:'https://menu.example.com'},clients:{claim:async()=>{}},skipWaiting:async()=>{},
      registration:{showNotification:async(...args)=>notices.push(args)},addEventListener:(name,fn)=>handlers[name]=fn},
    clients:{openWindow:async url=>opened.push(url)},fetch:async()=>{throw Error('offline')}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../static/store-worker355.js'),'utf8'),context);
  return {handlers,opened,notices};
}
test('store worker leaves other stores and POST requests alone',()=>{
  const {handlers}=worker();
  for(const [url,method] of [['https://menu.example.com/p/other/menu','GET'],['https://other.example.com/p/shop/menu','GET'],['https://menu.example.com/p/shop/menu/whatsapp','POST']]){
    handlers.fetch({request:{url,method,mode:'navigate'},respondWith:()=>assert.fail('worker intercepted unrelated request')});
  }
});
test('offline store navigation reports failure without queuing a purchase',async()=>{
  const {handlers}=worker();let pending;
  handlers.fetch({request:{url:'https://menu.example.com/p/shop/menu',method:'GET',mode:'navigate'},respondWith:p=>pending=p});
  const r=await pending;assert.equal(r.status,503);assert.match(await r.text(),/Nenhum pedido foi enviado/);
});
test('notification links remain confined to their store',async()=>{
  for(const target of ['https://evil.example.com/','/painel','/p/other/pedidos']){
    const {handlers,opened}=worker();let pending;
    handlers.notificationclick({notification:{data:{url:target},close(){}},waitUntil:p=>pending=p});
    await pending;assert.deepEqual(opened,['https://menu.example.com/p/shop/pedidos']);
  }
});
