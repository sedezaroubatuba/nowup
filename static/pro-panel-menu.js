(function () {
  function initPanelMenu() {
    const dashboard = document.querySelector('.pro-dashboard');
    if (!dashboard) return;

    const menuToggle = dashboard.querySelector('[data-pro-menu-toggle]');
    const sidebar = dashboard.querySelector('.pro-sidebar');
    const closeMenu = () => {
      dashboard.classList.remove('pro-menu-open');
      if (menuToggle) menuToggle.setAttribute('aria-expanded', 'false');
    };

    if (menuToggle && sidebar) {
      menuToggle.addEventListener('click', () => {
        const open = dashboard.classList.toggle('pro-menu-open');
        menuToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      });
    }

    dashboard.querySelectorAll('[data-copy-profile]').forEach(button => button.addEventListener('click', async () => {
      const url = new URL(button.dataset.profileUrl, window.location.origin).href;
      try { await navigator.clipboard.writeText(url); button.textContent = '✓ Link copiado'; }
      catch (_) { window.prompt('Copie o link do perfil:', url); }
      setTimeout(() => { button.textContent = '🔗 Copiar link'; }, 1800);
    }));
    dashboard.querySelectorAll('[data-cancel-form]').forEach(form => form.addEventListener('submit', event => {
      const reason = window.prompt('Informe o motivo da recusa:');
      if (!reason || !reason.trim()) { event.preventDefault(); return; }
      form.querySelector('[name="reason"]').value = reason.trim();
    }));
    dashboard.querySelectorAll('.order-status-form').forEach(form => form.addEventListener('submit', event => {
      const status = form.querySelector('[name="status"]')?.value;
      const reason = form.querySelector('[name="reason"]');
      if ((status === 'cancelled' || status === 'rejected') && !reason?.value.trim()) {
        event.preventDefault(); reason?.focus(); window.alert('Informe o motivo antes de cancelar ou recusar.');
      }
    }));
    dashboard.querySelectorAll('[data-print-order]').forEach(button => button.addEventListener('click', () => {
      const card = button.closest('.order-card');
      if (card) { card.classList.add('print-order-target'); window.print(); card.classList.remove('print-order-target'); }
    }));

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
        closeMenu();
      });
    });

    const revealOrder = () => {
      const hash=window.location.hash;
      if (hash === '#pedidos' || /^#pedido-\d+$/.test(hash)) {
        openFullDashboard(); closeMenu();
        const section=document.getElementById('pedidos');
        if(section){section.hidden=false;section.style.setProperty('display','block','important');}
        requestAnimationFrame(()=>document.getElementById(hash.slice(1))?.scrollIntoView({behavior:'smooth',block:'start'}));
      }
      activate(hash);
    };
    dashboard.querySelectorAll('a[href^="#pedido-"]').forEach(link=>link.addEventListener('click',()=>{openFullDashboard();setTimeout(revealOrder,0)}));
    revealOrder();
    window.addEventListener('hashchange', revealOrder);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPanelMenu);
  } else {
    initPanelMenu();
  }
})();
