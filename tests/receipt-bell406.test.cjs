const {test}=require('node:test');const assert=require('node:assert/strict');const {JSDOM}=require('jsdom');const fs=require('node:fs');const tick=()=>new Promise(r=>setImmediate(r));
test('accepted order stops active tones immediately and stale poll cannot restart them',async()=>{
 const dom=new JSDOM(`<div data-order-alerts data-latest-order-id="17"><button data-enable-order-alerts></button><span data-alert-status></span><button data-test-order-alerts></button><button data-disable-order-alerts></button></div><div data-new-order-alert hidden><span data-new-order-message></span><button data-open-new-order></button></div>`,{url:'https://nowup.test/painel',runScripts:'outside-only',pretendToBeVisual:true});
 const w=dom.window;let stops=0,starts=0,nextId=17;const intervals=[];
 w.localStorage.setItem('nowup-order-alerts','0');w.setInterval=fn=>{intervals.push(fn);return intervals.length;};
 w.AudioContext=class{constructor(){this.state='running';this.currentTime=0;this.destination={};}async resume(){}createOscillator(){return {frequency:{value:0},connect(node){return node;},start(){starts++;},stop(){stops++;}};}createGain(){return {gain:{setValueAtTime(){},exponentialRampToValueAtTime(){}},connect(){}};}};
 w.fetch=async()=>({ok:true,status:200,json:async()=>({latest_id:nextId,pending_count:1,pending_order:{id:nextId,customer_name:'Cliente teste',total_cents:4551}})});
 try{
  w.eval(fs.readFileSync('static/order-alerts.js','utf8'));await tick();
  w.document.querySelector('[data-enable-order-alerts]').click();await tick();await tick();
  assert.ok(starts>0);const before=stops;
  w.dispatchEvent(new w.CustomEvent('nowup:order-status',{detail:{id:17,status:'confirmed'}}));assert.ok(stops>before);assert.equal(w.document.querySelector('[data-new-order-alert]').hidden,true);
  await tick();await tick();assert.equal(w.document.querySelector('[data-new-order-alert]').hidden,true);
  const after=starts;intervals[1]();assert.equal(starts,after);
  nextId=18;await intervals[0]();await tick();assert.equal(w.document.querySelector('[data-new-order-alert]').hidden,false);assert.match(w.document.querySelector('[data-new-order-message]').textContent,/aguardando aceite/);
  const another=stops;w.dispatchEvent(new w.CustomEvent('nowup:order-status',{detail:{id:17,status:'confirmed'}}));assert.equal(stops,another);
 }finally{w.close();}
});
