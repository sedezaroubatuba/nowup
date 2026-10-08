/* Confirma a saída em qualquer tela, incluindo o menu lateral. */
(() => {
  'use strict';
  const isLogout = value => {
    try { const url = new URL(value, location.href); return url.origin === location.origin && url.pathname.replace(/\/+$/, '') === '/sair'; }
    catch (_) { return false; }
  };
  document.addEventListener('submit', event => {
    const form = event.target;
    const action = event.submitter?.getAttribute('formaction') || form.action;
    if (!isLogout(action)) return;
    if (!window.confirm('Tem certeza que deseja sair da sua conta do NowUp?')) {
      event.preventDefault();
      event.stopImmediatePropagation();
    }
  }, true);
  document.addEventListener('click', event => {
    const link = event.target.closest('a[href]');
    if (!link || !isLogout(link.href)) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    const form = document.createElement('form');
    form.method = 'post';
    form.action = '/sair';
    form.hidden = true;
    document.body.append(form);
    form.requestSubmit();
    form.remove();
  }, true);
})();
