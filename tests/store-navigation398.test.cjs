const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const store={slug:'shop',menu:'/p/shop/menu?loja=1',login:'/p/shop/entrar?tipo=cliente',signup:'/p/shop/cadastro',forgot:'/p/shop/recuperar-senha',orders:'/p/shop/pedidos',logout:'/p/shop/sair'};
const listeners={},context={URL,Request,location:{origin:'https://nowup.local',href:'https://nowup.local/p/shop/menu?loja=1'},window:{fetch:()=>{}},document:{getElementById:()=>({textContent:JSON.stringify(store)}),addEventListener:(name,f)=>listeners[name]=f}};
vm.runInNewContext(fs.readFileSync('static/store-session345.js','utf8'),context);
function click(path){const a={href:new URL(path,context.location.href).href};listeners.click({target:{closest:()=>a}});return a.href;}
assert.equal(click('/'),'https://nowup.local/p/shop/menu?loja=1');
assert.equal(click('/profissionais'),'https://nowup.local/p/shop/menu?loja=1');
assert.equal(click('/p/another-shop/menu'),'https://nowup.local/p/shop/menu?loja=1');
assert.equal(click('/p/shop/menu'),'https://nowup.local/p/shop/menu?loja=1');
assert.equal(click('/entrar'),'https://nowup.local/p/shop/entrar?tipo=cliente');
assert.equal(click('/pedido/opaque'),'https://nowup.local/p/shop/pedido/opaque');
assert.equal(click('/suporte'),'https://nowup.local/p/shop/suporte');
assert.equal(click('https://wa.me/5512999999999'),'https://wa.me/5512999999999');
console.log('PASS: store navigation stays exclusive; order and support keep store session; WhatsApp remains available');
