const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('fs');
const {JSDOM}=require('jsdom');
test('vitrine adds one unit, updates counter, obeys max and returns to plus at zero',()=>{
 const item={id:10,name:'Skol',price:4551,max:2,slug:'sede-zero',store:'Sede Zero',options:false};
 const dom=new JSDOM('<header><a data-vitrine-cart data-slug="sede-zero" hidden><span data-vitrine-count></span></a></header><main data-vitrine data-customer=""><p data-vitrine-status></p><div><button data-vitrine-item>+</button></div></main>',{runScripts:'outside-only',url:'https://nowup.local/'});
 const w=dom.window,d=w.document,button=d.querySelector('[data-vitrine-item]');button.dataset.vitrineItem=JSON.stringify(item);
 w.eval(fs.readFileSync('static/vitrine473.js','utf8'));
 const step=d.querySelector('.vitrine-step493'), minus=step.firstElementChild, plus=step.lastElementChild;
 assert.ok(step.hidden);button.click();assert.ok(button.hidden);assert.equal(step.querySelector('span').textContent,'1');plus.click();assert.equal(step.querySelector('span').textContent,'2');assert.equal(d.querySelector('header [data-vitrine-count]').textContent,'2');assert.ok(!d.querySelector('header [data-vitrine-cart]').hidden);assert.ok(plus.disabled);minus.click();minus.click();assert.ok(step.hidden);assert.ok(!button.hidden);assert.ok(d.querySelector('[data-vitrine-cart]').hidden);
 w.close();
});

test('single-item autoplay runs every 2s only on touch mobile, pauses after interaction and when hidden',()=>{
 const dom=new JSDOM('<main><div id="track"></div></main>',{runScripts:'outside-only',url:'https://nowup.local/',pretendToBeVisual:true});
 const w=dom.window,d=w.document,track=d.getElementById('track');
 let mobile=true,reduced=false,visible=true,now=10000,callback,delay,advances=0;
 w.matchMedia=query=>({get matches(){return query.includes('pointer')?mobile:reduced}});
 w.IntersectionObserver=class{constructor(cb){this.cb=cb;}observe(){this.cb([{isIntersecting:visible}]);}disconnect(){}};
 w.Date.now=()=>now;w.setInterval=(cb,ms)=>(callback=cb,delay=ms,1);
 Object.defineProperties(track,{scrollWidth:{value:900},clientWidth:{value:300}});
 track.getClientRects=()=>[{width:300,height:100}];
 w.eval(fs.readFileSync('static/carousel-autoplay501.js','utf8'));
 w.NowUpAutoSlide501.attach({track,advance:()=>advances++});
 assert.equal(delay,2000);callback();assert.equal(advances,1);
 mobile=false;callback();assert.equal(advances,1);
 mobile=true;reduced=true;callback();assert.equal(advances,1);
 reduced=false;track.dispatchEvent(new w.Event('click'));callback();assert.equal(advances,1);
 now+=5999;callback();assert.equal(advances,1);
 now+=1;callback();assert.equal(advances,2);
 const dialog=d.createElement('dialog');dialog.open=true;d.body.append(dialog);callback();assert.equal(advances,2);
 dialog.remove();callback();assert.equal(advances,3);
 w.close();
});
