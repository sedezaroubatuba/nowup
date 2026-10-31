(() => {
 'use strict';
 async function start(){
  const match=location.pathname.match(/^\/p\/([^/]+)(?:\/menu)?\/?$/);if(!match)return;
  const root=document.querySelector('[data-native-menu]');if(!root)return;
  try{
   const response=await fetch('/api/loja/'+encodeURIComponent(decodeURIComponent(match[1]))+'/banners207',{cache:'no-store'});if(!response.ok)return;
   const data=await response.json();if(!data.items?.length)return;
   // Wait for the existing storefront to build its home view.
   let tries=0;while(!document.body.dataset.store187Ready&&tries++<50)await new Promise(r=>setTimeout(r,100));
   if(!document.body.dataset.store187Ready)return;
   const section=document.createElement('section');section.className='nu207-banners';section.setAttribute('aria-label','Destaques da loja');
   const style=document.createElement('style');style.textContent='.nu207-banners{margin:16px 0;max-width:100%;position:relative}.nu207-track{display:flex;overflow-x:auto;scroll-snap-type:x mandatory;scrollbar-width:none;border-radius:16px}.nu207-card{flex:0 0 100%;min-width:0;scroll-snap-align:start;border:0;padding:0;background:#f5f3fa;cursor:pointer}.nu207-card img{display:block;width:100%;aspect-ratio:8/3;object-fit:cover}.nu207-controls{display:flex;justify-content:center;align-items:center;gap:10px;margin:8px}.nu207-controls button{min-width:44px;min-height:44px;border:1px solid #ddd;border-radius:12px;background:white;color:#59359c}body:not(.nu187-store-home) .nu207-banners{display:none}';document.head.append(style);
   const track=document.createElement('div');track.className='nu207-track';const controls=document.createElement('div');controls.className='nu207-controls';let index=0,timer,paused=false;
   data.items.forEach(item=>{const b=document.createElement('button');b.type='button';b.className='nu207-card';if(item.mode==='info'){b.disabled=true;b.style.cursor='default';b.style.opacity='1';}b.setAttribute('aria-label',item.title);const img=document.createElement('img');img.src=item.image;img.alt=item.title;img.addEventListener('error',()=>{img.hidden=true;b.textContent=item.title;});b.append(img);b.onclick=()=>item.mode!=='info'&&window.dispatchEvent(new CustomEvent('nowup-banner207',{detail:item}));track.append(b);});
   const button=(label,text,fn)=>{const b=document.createElement('button');b.type='button';b.textContent=text;b.setAttribute('aria-label',label);b.onclick=fn;return b;};
   const counter=document.createElement('span');counter.textContent='1 / '+data.items.length;
   function go(n){index=(n+data.items.length)%data.items.length;track.scrollTo({left:index*track.clientWidth,behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});}
   const pause=button('Pausar troca automática','Pausar',()=>{paused=!paused;pause.textContent=paused?'Reproduzir':'Pausar';pause.setAttribute('aria-label',paused?'Reproduzir troca automática':'Pausar troca automática');schedule();});
   function schedule(){clearInterval(timer);if(data.items.length>1&&!paused&&!document.hidden&&!section.matches(':hover')&&!section.contains(document.activeElement))timer=setInterval(()=>{if(document.body.classList.contains('nu187-store-home'))go(index+1);},Math.max(1,Math.min(120,Number(data.seconds)||2))*1000);}
   controls.append(button('Banner anterior','‹',()=>go(index-1)),counter,button('Próximo banner','›',()=>go(index+1)),pause);if(data.items.length===1)controls.hidden=true;
   track.addEventListener('scroll',()=>{index=Math.round(track.scrollLeft/Math.max(1,track.clientWidth));counter.textContent=(index+1)+' / '+data.items.length;},{passive:true});
   section.append(track,controls);const sticky=root.querySelector('.nu-menu-sticky');if(!sticky)return;sticky.after(section);window.dispatchEvent(new Event('nowup-slide-ready286'));
   section.addEventListener('mouseenter',schedule);section.addEventListener('mouseleave',schedule);section.addEventListener('focusin',schedule);section.addEventListener('focusout',()=>setTimeout(schedule,0));document.addEventListener('visibilitychange',schedule);window.addEventListener('pagehide',()=>clearInterval(timer));schedule();
  }catch(e){console.warn('Banners temporariamente indisponíveis');}
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();
