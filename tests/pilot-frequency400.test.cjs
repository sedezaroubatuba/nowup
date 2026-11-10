const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const code=fs.readFileSync('static/sede-zero-piloto383.js','utf8');
function storage(){const data=new Map();return {getItem:k=>data.get(k)||null,setItem:(k,v)=>data.set(k,v)}}
function open(now,local,session=storage()){
 const events={},close={hidden:false,addEventListener:(e,f)=>events['close-'+e]=f},image={complete:true,naturalWidth:1024},share={addEventListener:()=>{}},status={};
 const dialog={dataset:{shareUrl:'/p/adega-sede-zero/menu'},open:false,shows:0,querySelector:s=>s==='img'?image:s==='.nu383-close'?close:s==='.nu383-share'?share:status,showModal(){this.open=true;this.shows++},close(){this.open=false;events.close?.()},addEventListener:(e,f)=>events[e]=f};
 const window={localStorage:local,sessionStorage:session,addEventListener:()=>{}};
 vm.runInNewContext(code,{window,document:{getElementById:()=>dialog,activeElement:null},Date:{now:()=>now},Number,Array,JSON,URL,location:{origin:'https://nowup.local'},navigator:{},setInterval:()=>{throw new Error('Countdown is forbidden')}});
 return {dialog,close,events};
}
const local=storage(),first=open(100000,local);assert.equal(first.dialog.shows,1);assert.equal(first.close.hidden,false);first.events['close-click']();assert.equal(first.dialog.open,false);
const second=open(200000,local);assert.equal(second.dialog.shows,1);second.events.cancel({preventDefault(){}});assert.equal(second.dialog.open,false);
assert.equal(open(300000,local).dialog.shows,0);
assert.equal(open(100000+86400000,local).dialog.shows,1);
assert.equal(open(100001+86400000,local).dialog.shows,0);
const blocked={getItem(){throw new Error('disabled')},setItem(){throw new Error('disabled')}};
const session=storage();assert.equal(open(100000,blocked,session).dialog.shows,1);assert.equal(open(200000,blocked,session).dialog.shows,1);assert.equal(open(300000,blocked,session).dialog.shows,0);assert.equal(open(100000,blocked,blocked).dialog.shows,0);
console.log('PASS: immediate X, no countdown, close/Escape, two displays in rolling 24 hours, expiry and blocked-storage fallback');
