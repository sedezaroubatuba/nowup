(() => {
  let prompt;
  const standalone = () => matchMedia('(display-mode: standalone)').matches || navigator.standalone;
  function ready() {
    const button = document.createElement('button');
    button.textContent = 'Instalar NowUp ADM';
    button.type = 'button';
    button.style.cssText = 'position:fixed;bottom:20px;right:20px;width:auto;max-width:calc(100vw - 40px);margin:0;z-index:9999;border:1px solid #ab82ed;border-radius:12px;background:#53258c;color:white;padding:12px 16px;font:600 14px system-ui;cursor:pointer';
    button.hidden = standalone();
    document.body.append(button);
    addEventListener('beforeinstallprompt', event => { event.preventDefault(); prompt = event; button.hidden = standalone(); });
    addEventListener('appinstalled', () => { button.hidden = true; prompt = null; });
    button.onclick = async () => {
      if (prompt) { const current = prompt; prompt = null; await current.prompt(); await current.userChoice; }
      else alert('No Android: abra no Chrome e escolha Instalar aplicativo no menu. No computador: abra no Chrome ou Edge e procure Instalar este site como aplicativo. No iPhone: Safari → Compartilhar → Adicionar à Tela de Início.');
    };
    if (isSecureContext && 'serviceWorker' in navigator) navigator.serviceWorker.register('/nowup-push-sw.js', {scope:'/', updateViaCache:'none'}).catch(() => {});
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', ready); else ready();
})();
