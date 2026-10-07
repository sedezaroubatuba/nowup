(function () {
  'use strict';
  function init() {
    const root = document.getElementById('nu-admin');
    if (!root) return;
    const nav = document.getElementById('nu-admin-nav');
    const toggle = document.getElementById('nu-admin-toggle');
    const title = document.getElementById('nu-admin-title');
    const sections = Array.from(root.querySelectorAll('main > section.panel[id]'));
    const links = Array.from(nav.querySelectorAll('a[href^="#"]'));
    function remember(id) { try { sessionStorage.setItem('nowup-admin-area', id); } catch (_) {} }
    function saved() { try { return sessionStorage.getItem('nowup-admin-area'); } catch (_) { return null; } }
    function resolve(hash) {
      const id = hash.replace(/^#/, '');
      const target = document.getElementById(id);
      return sections.find(s => s.id === id || (target && s.contains(target)));
    }
    function close() { root.classList.remove('nav-open'); toggle.setAttribute('aria-expanded', 'false'); }
    function show(section, scroll) {
      sections.forEach(s => { s.hidden = s !== section; });
      links.forEach(a => {
        if (a.hash === '#' + section.id) a.setAttribute('aria-current', 'page');
        else a.removeAttribute('aria-current');
      });
      const active = links.find(a => a.hash === '#' + section.id);
      title.textContent = active ? active.textContent : 'Painel administrativo';
      remember(section.id); close();
      if (scroll) root.scrollIntoView({block: 'start'});
    }
    function fromLocation(scroll) { show(resolve(location.hash) || resolve(saved() || '') || sections[0], scroll); }
    links.forEach(a => a.addEventListener('click', e => {
      const section = resolve(a.hash);
      if (!section) return;
      e.preventDefault();
      if (location.hash !== a.hash) location.hash = a.hash;
      else show(section, true);
    }));
    toggle.addEventListener('click', () => {
      const open = root.classList.toggle('nav-open'); toggle.setAttribute('aria-expanded', String(open));
      if (open) nav.querySelector('a').focus();
    });
    document.addEventListener('keydown', e => { if (e.key === 'Escape') { close(); toggle.focus(); } });
    root.addEventListener('submit', e => {
      const section = e.target.closest('section.panel');
      if (section) remember(section.id);
    });
    window.addEventListener('hashchange', () => fromLocation(true));
    fromLocation(false);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
