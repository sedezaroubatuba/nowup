(()=>{'use strict';const original=document.getElementById('nowup-opening260');if(!original)return;
const node=document.getElementById('opening-config260');let cfg;try{cfg=JSON.parse(node.textContent);}catch(_){original.remove();return;}
const template=original.cloneNode(true);original.remove();
const duration=Math.max(2500,Math.min(6000,Number(cfg.duration)||4200)),color=/^#[0-9a-f]{6}$/i.test(cfg.color)?cfg.color:'#7136bf';
let active=null,hidden=false;
function play(){if(active)active();const el=template.cloneNode(true);document.body.append(el);let audio=null,finished=false,timer;
function stopAudio(){if(audio){audio.close().catch(()=>{});audio=null;}}
function close(){if(finished)return;finished=true;clearTimeout(timer);stopAudio();el.remove();document.removeEventListener('keydown',escape);if(active===close)active=null;}
function escape(e){if(e.key==='Escape')close();}active=close;
el.style.setProperty('--opening-color260',color);el.style.setProperty('--opening-duration260',duration+'ms');el.style.display='block';el.classList.add('playing');el.querySelector('[data-opening-skip260]').addEventListener('click',close);document.addEventListener('keydown',escape);
const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;timer=setTimeout(close,reduced?650:duration+100);
if(cfg.sound&&!reduced){el.addEventListener('pointerdown',e=>{if(e.target.closest('[data-opening-skip260]')||finished)return;const AC=window.AudioContext||window.webkitAudioContext;if(!AC)return;try{audio=new AC();audio.resume().catch(()=>{});const t=audio.currentTime;function tone(at,len,freq,type,gain,end){const osc=audio.createOscillator(),amp=audio.createGain();osc.type=type;osc.frequency.setValueAtTime(freq,t+at);if(end)osc.frequency.exponentialRampToValueAtTime(end,t+at+len);amp.gain.setValueAtTime(.0001,t+at);amp.gain.exponentialRampToValueAtTime(gain,t+at+.025);amp.gain.exponentialRampToValueAtTime(.0001,t+at+len);osc.connect(amp).connect(audio.destination);osc.start(t+at);osc.stop(t+at+len+.02);}for(const at of [0,.2]){tone(at,.15,430,'triangle',.09);tone(at,.15,330,'square',.022);}tone(.45,.65,75,'sawtooth',.035,210);}catch(_){}},{once:true});}

}
// Same-tab navigation is not a new app entry. Hidden -> visible is.
let navigation=false;try{navigation=sessionStorage.getItem('nowup-internal-navigation')==='1';sessionStorage.removeItem('nowup-internal-navigation');}catch(_){}
if(!navigation||cfg.preview)play();
document.addEventListener('visibilitychange',()=>{if(document.hidden){hidden=true;if(active)active();}else if(hidden){hidden=false;play();}});
window.addEventListener('pagehide',()=>{if(active)active();});
window.addEventListener('pageshow',e=>{if(e.persisted&&hidden){hidden=false;play();}});
function loading(){if(document.getElementById('nowup-wait256'))return;const box=document.createElement('div');box.id='nowup-wait256';box.setAttribute('role','status');box.setAttribute('aria-label','Carregando');box.innerHTML='<div class="wait-bike"></div><p>Carregando…</p>';box.querySelector('.wait-bike').append(template.querySelector('.motorbike').cloneNode(true));document.body.append(box);setTimeout(()=>{if(box.isConnected){box.querySelector('p').textContent='Está demorando um pouco. Aguarde ou volte à tela anterior.';const b=document.createElement('button');b.textContent='Fechar';b.onclick=()=>box.remove();box.append(b);}},12000);}
let waiting;function begin(){try{sessionStorage.setItem('nowup-internal-navigation','1');}catch(_){}waiting=setTimeout(loading,650);}
document.addEventListener('click',e=>{const a=e.target.closest('a[href]');if(!a||e.defaultPrevented||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey||a.download||a.target&&a.target!=='_self')return;const u=new URL(a.href,location.href);if(u.origin!==location.origin||u.pathname===location.pathname&&u.search===location.search)return;begin();});
document.addEventListener('submit',e=>{if(!e.defaultPrevented)begin();});
window.addEventListener('pageshow',()=>{clearTimeout(waiting);document.getElementById('nowup-wait256')?.remove();});
})();