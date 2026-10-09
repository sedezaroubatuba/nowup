/* V82 admin navigation: independent of other panel assets. */
(()=>{'use strict';
const init=()=>{
 const root=document.getElementById('nu-admin'),nav=document.getElementById('nu-admin-nav'),toggle=document.getElementById('nu-admin-toggle');
 if(!root||!nav||!toggle)return;
 const sections=[...root.querySelectorAll('main > section.panel[id]')];
 const setOpen=open=>{root.classList.toggle('nav-open',open);toggle.setAttribute('aria-expanded',String(open));toggle.setAttribute('aria-label',open?'Fechar menu administrativo':'Abrir menu administrativo');};
 const show=()=>{
  const id=decodeURIComponent(location.hash.slice(1)||'dashboard');
  const target=document.getElementById(id);
  const section=sections.find(s=>s===target||s.contains(target))||sections.find(s=>s.id==='dashboard');
  sections.forEach(s=>s.hidden=s!==section);
  nav.querySelectorAll('a[href^="#"]').forEach(a=>{if(a.hash==='#'+section?.id)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});
  const title=document.getElementById('nu-admin-title');if(title)title.textContent=section?.querySelector('h1,h2')?.textContent||'Painel administrativo';
 };
 toggle.addEventListener('click',e=>{e.preventDefault();setOpen(!root.classList.contains('nav-open'));});
 nav.addEventListener('click',e=>{if(e.target.closest('a[href]'))setOpen(false);});
 document.addEventListener('keydown',e=>{if(e.key==='Escape')setOpen(false);});
 window.addEventListener('hashchange',show);show();setOpen(false);
};if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
