function acceptCookies(){localStorage.setItem('nowup_cookies','1');const e=document.getElementById('cookie');if(e)e.remove()}
document.addEventListener('DOMContentLoaded',()=>{
  if(localStorage.getItem('nowup_cookies')){const e=document.getElementById('cookie');if(e)e.remove()}
  const slider=document.querySelector('[data-slider]');
  if(!slider)return;
  const slides=[...slider.querySelectorAll('.ad-slide')],dots=[...slider.querySelectorAll('[data-slide]')];
  let current=0,timer;
  const show=i=>{current=(i+slides.length)%slides.length;slides.forEach((s,n)=>s.classList.toggle('active',n===current));dots.forEach((d,n)=>d.classList.toggle('active',n===current))};
  const start=()=>{clearInterval(timer);if(slides.length>1)timer=setInterval(()=>show(current+1),5000)};
  dots.forEach((d,i)=>d.addEventListener('click',()=>{show(i);start()}));start();
})
