const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const {JSDOM}=require('jsdom');
test('fashion search and categories reuse compact cards and preserve visible cart controls',()=>{
 const dom=new JSDOM('<body class="public-profile-area fashion-catalog385"><section data-native-menu><div class="nu-menu-sticky"><input data-product-search><nav><button data-category-filter="all">Todos</button><button data-category-filter="vestidos">Vestidos</button><button data-category-filter="tenis">Tênis</button></nav></div><div id="intro"></div><div id="showcase"></div><div id="category"></div><div id="layout"></div><button id="back"></button></section></body>',{runScripts:'outside-only'}),w=dom.window,d=w.document;
 w.requestAnimationFrame=fn=>{fn();return 1;};w.HTMLElement.prototype.scrollIntoView=function(){};
 w.eval(fs.readFileSync('static/fashion-layout391.js','utf8'));
 const root=d.querySelector('section'),search=root.querySelector('input'),nav=root.querySelector('nav');
 const sources=[['1','Vestido midi','vestidos'],['2','Tênis casual','tenis'],['3','Vestido preto','vestidos']].map(([id,name,category])=>{const c=d.createElement('article');Object.assign(c.dataset,{id,name,category});return c;});
 let calls=0;function compact(source){calls++;const c=d.createElement('article');c.dataset.source256=source.dataset.id;c.className='nu201-card';c.innerHTML='<h3>'+source.dataset.name+'</h3><div class="nu-step263"><button>−</button><span>1</span><button>+</button></div>';return c;}
 w.NOWUP_FASHION_LAYOUT391({root,originals:sources,compact,sticky:root.firstElementChild,nav,intro:d.querySelector('#intro'),showcase:d.querySelector('#showcase'),categoryView:d.querySelector('#category'),layout:d.querySelector('#layout'),back:d.querySelector('#back'),cartRefreshers:[],search});
 const nodes=[...d.querySelectorAll('.nu391-fashion-card')];assert.equal(calls,3);
 nav.querySelector('[data-category-filter="vestidos"]').click();assert.deepEqual(nodes.filter(c=>!c.hidden).map(c=>c.dataset.source256),['1','3']);assert.equal(nodes[1].style.getPropertyValue('display'),'none');assert.equal(nodes[1].style.getPropertyPriority('display'),'important');
 search.value='preto';search.dispatchEvent(new w.Event('input',{bubbles:true}));assert.deepEqual(nodes.filter(c=>!c.hidden).map(c=>c.dataset.source256),['3']);
 assert.equal(d.querySelectorAll('.nu391-fashion-card').length,3);assert.equal(calls,3);assert.equal(nodes[2].querySelector('.nu-step263').hidden,false);
 search.value='';nav.querySelector('[data-category-filter="tenis"]').click();assert.deepEqual(nodes.filter(c=>!c.hidden).map(c=>c.dataset.source256),['2']);
 assert.equal(d.querySelectorAll('.nu190-track').length,0);dom.window.close();
});
