/* V457: update the active merchant shortcut without changing panel navigation. */
(()=>{'use strict';
 const nav=document.querySelector('.nu457-merchant-bottom');
 if(!nav)return;
 function sync(){
  const onHistory=location.pathname==='/painel/todos-produtos';
  const hash=location.hash;
  let current=onHistory?'historico':/^#(?:pedidos-ativos|pedido-\d+|pedidos)$/.test(hash)?'pedidos':
   /^#(?:cardapio|produtos-loja|novo-produto|categorias-loja|cadastrar-combo|combos-loja|agrupadores260|lanches-refeicoes322|novo-lanche322|produtos-peso370|peso-loja|adicionais)$/.test(hash)?'cadastro':'inicio';
  nav.querySelectorAll('a[data-merchant-tab457]').forEach(a=>{
   if(a.dataset.merchantTab457===current)a.setAttribute('aria-current','page');
   else a.removeAttribute('aria-current');
  });
 }
 window.addEventListener('hashchange',sync);window.addEventListener('popstate',sync);
 window.addEventListener('nowup:panelnavigate',sync);
 nav.addEventListener('click',event=>{
  const a=event.target.closest('a[href]');
  if(!a||location.pathname!=='/painel')return;
  const url=new URL(a.href);
  if(url.pathname!==location.pathname||!url.hash||url.hash===location.hash)return;
  requestAnimationFrame(sync);
 });
 sync();
})();
