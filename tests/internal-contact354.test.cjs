const test=require('node:test'),assert=require('node:assert/strict'),fs=require('fs'),{JSDOM}=require('jsdom');
const code=fs.readFileSync('static/internal-contact106.js','utf8');
for(const mode of ['catalogue','merchant','marketplace'])test('legacy contact policy respects '+mode+' context',async()=>{
 const context=mode==='catalogue'?'<script id="store-app256" type="application/json">{"slug":"shop"}</script>':mode==='merchant'?'<div class="pro-dashboard"></div>':'';
 const dom=new JSDOM(`<body>${context}<form action="/p/shop/menu/whatsapp"><button>Finalizar</button></form></body>`,{url:'https://nowup.local/p/shop/menu',runScripts:'outside-only'});
 try{dom.window.eval(code);const form=dom.window.document.querySelector('form');assert.equal(form.hidden,mode==='marketplace');
 const a=dom.window.document.createElement('a');a.href='https://wa.me/5512999999999?text=pedido';a.textContent='Enviar';dom.window.document.body.append(a);await new Promise(r=>setTimeout(r,0));assert.equal(a.hidden,mode==='marketplace');
 }finally{dom.window.close();}
});
