/* V198 merchant navigation: restored missing asset. */
(() => {
 'use strict';
 function init(){
  const root=document.querySelector('.pro-dashboard');if(!root||root.dataset.nav198==='ready')return;
  const main=root.querySelector('main');if(!main)return;
  const sections=Array.from(main.children).filter(e=>e.tagName==='SECTION'&&e.id);
  function close(){
   root.classList.remove('nu198-menu-open','pro-menu-open');
   root.querySelector('[data-pro-menu-toggle]')?.setAttribute('aria-expanded','false');
   const shade=root.querySelector('.v60-shade');if(shade)shade.hidden=true;
  }
  function navigate(hash,scroll=true){
   let key;try{key=decodeURIComponent((hash||'#inicio').slice(1));}catch(_){return false;}
   key=key||'inicio';if(key==='hoje')key='pedidos-ativos';if(key==='pratos')key='cardapio';
   let target=document.getElementById(key);
   if(!target&&['produtos-loja','novo-produto','categorias-loja','acompanhamentos-combos'].includes(key))target=document.getElementById('cardapio');
   if(!target||!main.contains(target))return false;
   const parent=sections.find(s=>s===target||s.contains(target));if(!parent)return false;
   const groups={inicio:['inicio','pedidos-ativos'],resumo:['resumo','estatisticas'],relatorios:['relatorios','mais-pedidos'],perfil:['perfil','identidade','fotos','publicidade']};
   const visibleIds=groups[key]||[parent.id];
   sections.forEach(s=>{const visible=visibleIds.includes(s.id);s.dataset.visible198=String(visible);s.hidden=!visible;s.style.setProperty('display',visible?(s.id==='estatisticas'?'grid':'block'):'none','important');});
   for(let e=target;e&&e!==main;e=e.parentElement)if(e.tagName==='DETAILS')e.open=true;
   document.querySelectorAll('a[data-nav198]').forEach(a=>{const active=a.hash==='#'+key||(a.hash==='#produtos-loja'&&parent.id==='cardapio');if(active)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});
   close();if(scroll)requestAnimationFrame(()=>target.scrollIntoView({block:'start',behavior:'auto'}));
   return true;
  }
  window.addEventListener('click',event=>{
   const node=event.target.closest?.('a,button');if(!node)return;
   if(root.contains(node)&&node.matches('[data-pro-menu-toggle]')){
    event.preventDefault();event.stopImmediatePropagation();
    const open=!root.classList.contains('nu198-menu-open');close();root.classList.toggle('nu198-menu-open',open);
    node.setAttribute('aria-expanded',String(open));const shade=root.querySelector('.v60-shade');if(shade)shade.hidden=!open;return;
   }
   if(root.contains(node)&&node.matches('[data-close-pro-menu]')){event.preventDefault();event.stopImmediatePropagation();close();return;}
   if(node.matches('[data-panel-back-top]')){event.preventDefault();event.stopImmediatePropagation();window.scrollTo({top:0,behavior:'smooth'});return;}
   if(node.tagName==='A'&&(root.contains(node)||node.closest('.nu198-bottom'))&&node.getAttribute('href')?.startsWith('#')){
    if(navigate(node.hash)){event.preventDefault();event.stopImmediatePropagation();if(location.hash!==node.hash)history.pushState(null,'',node.hash);}
   }
  },true);
  window.addEventListener('hashchange',()=>navigate(location.hash));
  window.addEventListener('popstate',()=>navigate(location.hash));
  window.addEventListener('nowup:panelnavigate',()=>navigate(location.hash));
  window.addEventListener('keydown',event=>{if(event.key==='Escape')close();});
  root.dataset.nav198='ready';
  if(!navigate(location.hash||'#inicio',false))navigate('#inicio',false);
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();

