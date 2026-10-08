(() => {
  const bells = [...document.querySelectorAll('[data-sales-bell]')];
  if (!bells.length) return;
  let busy = false;
  const poll = async () => {
    if (busy || document.hidden) return;
    busy = true;
    try {
      const response = await fetch('/admin/vendas/avisos', {credentials:'same-origin', cache:'no-store'});
      if (!response.ok) throw new Error('request failed');
      const {alerts} = await response.json();
      bells.forEach(bell => {
        bell.querySelector('[data-alert-count]').textContent = `(${alerts.length})`;
        const list = bell.querySelector('[data-alert-list]'); list.replaceChildren();
        if (!alerts.length) list.textContent = 'Nenhum aviso de vendas neste momento.';
        alerts.forEach(item => {
          const article = document.createElement('article');
          const name = document.createElement('strong'); name.textContent = item.name;
          const title = document.createElement('span'); title.textContent = item.title;
          const message = document.createElement('small'); message.textContent = item.message;
          const link = document.createElement('a'); link.textContent = 'Abrir relatório da loja →'; link.href = item.link;
          article.append(name,title,message,link); list.append(article);
        });
      });
    } catch (_) {
      bells.forEach(bell => { bell.querySelector('[data-alert-count]').textContent = ''; bell.querySelector('[data-alert-list]').textContent = 'Não foi possível consultar. Confira sua sessão e tente novamente.'; });
    } finally { busy = false; }
  };
  bells.forEach(bell => bell.addEventListener('toggle',()=>{if(bell.open) poll();}));
  document.addEventListener('visibilitychange',poll);
  poll();setInterval(poll,60000);
})();
