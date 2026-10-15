(() => {
  'use strict';
  if(window.__nowupPWA184)return;window.__nowupPWA184=true;
  let installPrompt = null;
  let installedHere = false;
  const standalone = () => installedHere || matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
  const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  const embedded = /FBAN|FBAV|Instagram|; wv\)/i.test(navigator.userAgent);
  const mobile = /Android|iPhone|iPad|iPod/.test(navigator.userAgent) || isIOS;
  const dismissed = () => { try { return sessionStorage.getItem('nowup-install-dismissed184') === '1'; } catch (_) { return false; } };
  function refresh() {
    const bar = document.getElementById('nowup-install-bar');
    if (bar) bar.hidden = standalone() || dismissed() || !(mobile || installPrompt) || !(location.pathname === '/' || location.pathname === '/entrar' || location.pathname === '/cliente');
    document.querySelectorAll('[data-nowup-install]').forEach(button => { button.hidden = standalone(); });
  }
  window.addEventListener('beforeinstallprompt', event => { event.preventDefault(); installPrompt = event; refresh(); });
  window.addEventListener('appinstalled', () => { installedHere = true; installPrompt = null; refresh(); });
  document.addEventListener('click', async event => {
    if (!event.target.closest('[data-nowup-install]')) return;
    if (standalone()) return;
    if (installPrompt) {
      const prompt = installPrompt; installPrompt = null;
      try { await prompt.prompt(); await prompt.userChoice; } catch (_) { showHelp(); }
      refresh();
    } else showHelp();
  });
  function showHelp() {
    const dialog = document.getElementById('nowup-install-help');
    const text = document.getElementById('nowup-install-instructions');
    if (!dialog || !text) return;
    text.textContent = embedded ? 'Abra este endereço no Chrome (Android) ou Safari (iPhone), usando o menu do navegador deste aplicativo. Depois procure Instalar aplicativo ou Adicionar à Tela de Início.' : isIOS ? 'No iPhone ou iPad, abra o menu Compartilhar e escolha Adicionar à Tela de Início. Se a opção não aparecer, abra este site no Safari.' : 'Abra o menu do navegador (⋮) e procure Instalar aplicativo ou Adicionar à tela inicial. Se a opção não aparecer, abra o site no Chrome ou aguarde o carregamento e tente novamente.';
    if (typeof dialog.showModal === 'function') { if (!dialog.open) dialog.showModal(); } else alert(text.textContent);
  }
  document.getElementById('nowup-install-dismiss')?.addEventListener('click', () => { try { sessionStorage.setItem('nowup-install-dismissed184', '1'); } catch (_) {} const bar = document.getElementById('nowup-install-bar'); if (bar) bar.hidden = true; });
  if (standalone() || new URLSearchParams(location.search).get('pwa') === '1') document.documentElement.classList.add('nowup-installed');
  refresh();
  if (window.isSecureContext && 'serviceWorker' in navigator) {
    navigator.serviceWorker.register('/nowup-push-sw.js', {scope: '/', updateViaCache: 'none'}).then(registration => {
      // Ask for updates without reloading an active cart or form.
      registration.update().catch(() => {});
      document.addEventListener('visibilitychange', () => { if (!document.hidden) registration.update().catch(() => {}); });
    }).catch(() => { /* Website remains available when installation is unsupported. */ });
  }
})();
