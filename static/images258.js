/* Load catalog images near the viewport, including cloned carousel cards. */
(()=>{'use strict';
 let observer;const selector='img[data-src258]';
 function reveal(img){const src=img.dataset.src258;if(!src)return;img.removeAttribute('data-src258');img.decoding='async';img.src=src;observer?.unobserve(img);}
 if('IntersectionObserver' in window)observer=new IntersectionObserver(entries=>entries.forEach(e=>{if(e.isIntersecting)reveal(e.target);}),{rootMargin:'250px',threshold:0.01});
 function watch(img){if(img.matches?.(selector)){if(observer)observer.observe(img);else reveal(img);}}
 function scan(node){watch(node);node.querySelectorAll?.(selector).forEach(watch);}
 function start(){scan(document.documentElement);new MutationObserver(records=>records.forEach(r=>r.addedNodes.forEach(scan))).observe(document.body,{childList:true,subtree:true});}
 window.NOWUP_IMAGES258={watch};
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
