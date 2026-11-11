const {test}=require('node:test');
const assert=require('node:assert/strict');
const {JSDOM}=require('jsdom');
const fs=require('node:fs');
const source=fs.readFileSync('static/merchant228.js','utf8');
const board=label=>`<div class="mk228-board"><button data-stage228="new">Recebidos</button><div data-column228="new"><article data-card228 data-search228="${label}">${label}</article><span class="mk228-no-match" hidden></span></div></div>`;
const tick=()=>new Promise(resolve=>setImmediate(resolve));

test('unchanged refresh preserves merchant card nodes; changed response updates them',async()=>{
 const dom=new JSDOM(`<div data-merchant228><aside class="pro-sidebar"></aside><button data-pro-menu-toggle></button><section id="pedidos-ativos"><div class="mk228-heading"></div><input data-search-input228><p data-live228></p><button data-refresh228>Atualizar</button><div data-board228>${board('Inicial')}</div></section></div>`,{url:'https://nowup.test/painel',runScripts:'outside-only',pretendToBeVisual:true});
 const w=dom.window;w.matchMedia=()=>({matches:false,addEventListener(){}});
 w.setInterval=()=>1;w.clearInterval=()=>{};
 const queue=[board('Pedido A'),board('Pedido A'),board('Pedido B')];
 w.fetch=async()=>({ok:true,status:200,redirected:false,text:async()=>queue.shift()});
 w.eval(source);
 const refresh=async()=>{w.document.querySelector('[data-refresh228]').click();await tick();await tick();};
 try{
  await refresh();const original=w.document.querySelector('[data-card228]');
  assert.equal(original.textContent,'Pedido A');
  await refresh();assert.equal(w.document.querySelector('[data-card228]'),original);
  await refresh();assert.notEqual(w.document.querySelector('[data-card228]'),original);
  assert.equal(w.document.querySelector('[data-card228]').textContent,'Pedido B');
 }finally{w.close();}
});
