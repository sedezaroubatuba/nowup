(()=>{'use strict';const original=document.getElementById('nowup-opening260');if(!original)return;
const node=document.getElementById('opening-config260');let cfg;try{cfg=JSON.parse(node.textContent);}catch(_){original.remove();return;}
const template=original.cloneNode(true);original.remove();
const mode=cfg.mode||'bike',scope=cfg.scope||'nowup';
const duration=mode==='nowup'?3800:mode==='sede'?1800:Math.max(2500,Math.min(6000,Number(cfg.duration)||4200)),color=/^#[0-9a-f]{6}$/i.test(cfg.color)?cfg.color:'#7136bf';
let active=null,hidden=false;
function play(){if(active)active();const el=template.cloneNode(true);document.body.append(el);let audio=null,finished=false,timer;
function stopAudio(){if(audio){audio.close().catch(()=>{});audio=null;}}
function close(){if(finished)return;finished=true;clearTimeout(timer);stopAudio();el.remove();document.removeEventListener('keydown',escape);if(active===close)active=null;}
function escape(e){if(e.key==='Escape')close();}active=close;
el.style.setProperty('--opening-color260',color);el.style.setProperty('--opening-duration260',duration+'ms');el.style.display='block';el.classList.add('playing');el.querySelector('[data-opening-skip260]').addEventListener('click',close);document.addEventListener('keydown',escape);
const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;timer=setTimeout(close,reduced?650:duration+100);
if(mode==='bike'&&cfg.sound&&!reduced){el.addEventListener('pointerdown',e=>{if(e.target.closest('[data-opening-skip260]')||finished)return;const AC=window.AudioContext||window.webkitAudioContext;if(!AC)return;try{audio=new AC();audio.resume().catch(()=>{});const t=audio.currentTime;function tone(at,len,freq,type,gain,end){const osc=audio.createOscillator(),amp=audio.createGain();osc.type=type;osc.frequency.setValueAtTime(freq,t+at);if(end)osc.frequency.exponentialRampToValueAtTime(end,t+at+len);amp.gain.setValueAtTime(.0001,t+at);amp.gain.exponentialRampToValueAtTime(gain,t+at+.025);amp.gain.exponentialRampToValueAtTime(.0001,t+at+len);osc.connect(amp).connect(audio.destination);osc.start(t+at);osc.stop(t+at+len+.02);}for(const at of [0,.2]){tone(at,.15,430,'triangle',.09);tone(at,.15,330,'square',.022);}tone(.45,.65,75,'sawtooth',.035,210);}catch(_){}},{once:true});}

}
// One opening per app/store session; navigation and checkout never replay it.
function start(){
 const key='nowup-opening-session488:'+scope;
 let first=true;try{first=sessionStorage.getItem(key)!=='1';sessionStorage.setItem(key,'1');}catch(_){try{first=!document.referrer||new URL(document.referrer).origin!==location.origin;}catch(_){first=true;}}
 if(first||cfg.preview)play();
}
start();
document.addEventListener('visibilitychange',()=>{if(document.hidden&&active)active();});
window.addEventListener('pagehide',()=>{if(active)active();});
})();
