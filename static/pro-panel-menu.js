(function () {
  function initPanelMenu() {
    const dashboard = document.querySelector('.pro-dashboard');
    if (!dashboard) return;

    const links = [...dashboard.querySelectorAll('.pro-sidebar a[href^="#"]')];
    if (!links.length) return;

    const openFullDashboard = () => {
      dashboard.classList.add('show-full-dashboard');
      const toggle = dashboard.querySelector('[data-toggle-pro-dashboard]');
      if (toggle) {
        toggle.setAttribute('aria-expanded', 'true');
        toggle.textContent = '🧾 Voltar para pedidos';
      }
    };

    const activate = (hash) => {
      links.forEach((link) => link.classList.toggle('active', link.hash === hash));
    };

    links.forEach((link) => {
      link.addEventListener('click', () => {
        openFullDashboard();
        activate(link.hash);
        document.body.classList.remove('menu-open');
      });
    });

    if (window.location.hash) activate(window.location.hash);
    window.addEventListener('hashchange', () => activate(window.location.hash));
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPanelMenu);
  } else {
    initPanelMenu();
  }
})();
