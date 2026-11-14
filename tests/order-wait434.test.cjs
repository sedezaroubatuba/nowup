const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),{JSDOM,VirtualConsole}=require('jsdom');
const html=`<article class="order-card"><section data-wait434 data-order-id434="7" data-endpoint434="/p/store/pedido/token/espera434" data-status434="new" data-customer434="1"><strong data-title434></strong><div data-clock434></div><p data-message434></p><button data-handoff434 hidden>Continuar pelo WhatsApp</button><a data-whatsapp434 hidden></a><p data-feedback434></p></section></article>`;
const flush=()=>new Promise(r=>setImmediate(r));
test('server time controls countdown; WhatsApp stays secondary until expiry and selection is idempotent',async()=>{
 const dom=new JSDOM(html,{url:'https://nowup.local/',runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:new VirtualConsole()}),w=dom.window;let status='new',left=42000,posts=0;const loops=[];w.setInterval=fn=>{loops.push(fn);return loops.length;};
 w.fetch=async(url,opt={})=>{if(opt.method==='POST'){posts++;status='whatsapp_finalized';}return {ok:true,json:async()=>({status,server_now:'2026-11-14T12:00:00Z',deadline:new Date(Date.parse('2026-11-14T12:00:00Z')+left).toISOString(),available:true,whatsapp_url:status==='whatsapp_finalized'?'https://wa.me/5512999999999?text=same-order':''})};};
 w.eval(fs.readFileSync('static/order-wait434.js','utf8'));await flush();
 const d=w.document,button=d.querySelector('[data-handoff434]');assert.equal(d.querySelector('[data-clock434]').textContent,'00:42');assert.equal(button.hidden,true);
 // A local device clock far from the server must not enable WhatsApp early.
 assert.equal(d.querySelector('[data-whatsapp434]').hidden,true);
 left=-1000;w.dispatchEvent(new w.Event('focus'));await flush();assert.equal(button.hidden,false);assert.equal(d.querySelector('[data-clock434]').textContent,'00:00');
 button.click();button.click();await flush();assert.equal(posts,1);assert.equal(button.hidden,true);assert.equal(d.querySelector('[data-whatsapp434]').hidden,false);assert.match(d.querySelector('[data-message434]').textContent,/Aceite e pagamento bloqueados/);dom.window.close();
});
test('merchant sees the same deadline and existing accept buttons are disabled after handoff',async()=>{
 const merchant=html.replace('data-customer434="1"','data-customer434="0"').replace('</article>','<form action="/painel/pedidos/7/status"><button>Aceitar pedido</button></form></article>');
 const dom=new JSDOM(merchant,{url:'https://nowup.local/',runScripts:'outside-only',pretendToBeVisual:true}),w=dom.window;let status='new';w.setInterval=()=>1;
 w.fetch=async()=>({ok:true,json:async()=>({status,server_now:new Date().toISOString(),deadline:new Date(Date.now()+42000).toISOString(),available:true})});
 w.eval(fs.readFileSync('static/order-wait434.js','utf8'));await flush();assert.equal(w.document.querySelector('[data-clock434]').textContent,'00:42');status='whatsapp_finalized';w.dispatchEvent(new w.Event('focus'));await flush();assert.equal(w.document.querySelector('form button').disabled,true);w.close();
});
