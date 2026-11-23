const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('fs'),{JSDOM}=require('jsdom');
const code=fs.readFileSync('static/merchant-bottom457.js','utf8');
function setup(url){const html='<nav class="nu457-merchant-bottom">'+[['inicio','/painel#inicio'],['historico','/painel/todos-produtos'],['cadastro','/painel#cardapio'],['pedidos','/painel#pedidos-ativos']].map(([id,href])=>`<a data-merchant-tab457="${id}" href="${href}">${id}</a>`).join('')+'</nav>';const dom=new JSDOM(html,{url,runScripts:'outside-only'});dom.window.eval(code);return dom;}
function active(dom){return [...dom.window.document.querySelectorAll('[aria-current=page]')].map(x=>x.dataset.merchantTab457);}
test('history page marks history shortcut',()=>{const dom=setup('https://nowupbrasil.com/painel/todos-produtos');assert.deepEqual(active(dom),['historico']);dom.window.close();});
test('merchant orders shortcut is selected',()=>{const dom=setup('https://nowupbrasil.com/painel#pedidos-ativos');assert.deepEqual(active(dom),['pedidos']);dom.window.close();});
test('merchant catalogue shortcut responds to hash change',()=>{const dom=setup('https://nowupbrasil.com/painel#inicio');dom.window.history.replaceState(null,'','#cardapio');dom.window.dispatchEvent(new dom.window.Event('hashchange'));assert.deepEqual(active(dom),['cadastro']);dom.window.close();});
