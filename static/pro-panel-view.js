(function(){
  const dashboard=document.querySelector('.pro-dashboard');
  const button=document.querySelector('[data-toggle-pro-dashboard]');
  if(!dashboard||!button)return;
  const setFull=(full)=>{
    dashboard.classList.toggle('show-full-dashboard',full);
    button.setAttribute('aria-expanded',String(full));
    button.textContent=full?'🧾 Voltar para pedidos':'📊 Ver todos os relatórios';
  };
  const hash=window.location.hash;
  const orderHashes=['#pedidos','#pedidos-ativos'];
  let full=false;
  if(hash&&!orderHashes.some(item=>hash.startsWith(item))&&!hash.startsWith('#pedido-'))full=true;
  setFull(full);
  button.addEventListener('click',()=>{
    const next=!dashboard.classList.contains('show-full-dashboard');
    setFull(next);
    window.scrollTo({top:0,behavior:'smooth'});
  });
  dashboard.querySelectorAll('.pro-sidebar a[href^="#"]').forEach(link=>link.addEventListener('click',()=>setFull(true)));
})();
