(() => {
  const normalize = value => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  document.querySelectorAll('[data-filter-group]').forEach(group => {
    const name = group.dataset.filterGroup;
    const rows = [...document.querySelectorAll(`[data-v72-row="${name}"]`)];
    const search = document.querySelector(`[data-search="${name}"]`);
    const result = document.querySelector(`[data-result="${name}"]`);
    let selected = 'all';
    const matches = (row, filter) => filter === 'all' || (name === 'profiles' && filter === 'demo' ? row.dataset.demo === '1' : row.dataset.status === filter);
    const update = () => {
      const term = normalize(search.value.trim());
      let shown = 0;
      rows.forEach(row => { row.hidden = !(matches(row, selected) && normalize(row.dataset.searchText).includes(term)); if (!row.hidden) shown++; });
      group.querySelectorAll('[data-filter]').forEach(button => {
        button.setAttribute('aria-pressed', String(button.dataset.filter === selected));
        button.querySelector('[data-count]').textContent = `(${rows.filter(row => matches(row, button.dataset.filter)).length})`;
      });
      result.textContent = shown ? `${shown} perfil(is) encontrado(s).` : 'Nenhum perfil encontrado neste filtro.';
    };
    group.addEventListener('click', event => { const button = event.target.closest('[data-filter]'); if (button) { selected = button.dataset.filter; update(); } });
    search.addEventListener('input', update);
    update();
  });
})();
// Include the new Financeiro area in existing administrative navigation.
(() => {
  const root = document.getElementById('nu-admin');
  if (!root) return;
  const panels = [...root.querySelectorAll('main > section.panel')];
  const activate = () => {
    const id = location.hash.slice(1) || 'dashboard';
    const target = document.getElementById(id);
    const active = target && (panels.includes(target) ? target : target.closest('section.panel'));
    const current = panels.includes(active) ? active : panels.find(p => p.id === 'dashboard');
    panels.forEach(panel => { panel.hidden = panel !== current; panel.style.setProperty('display', panel === current ? 'block' : 'none', 'important'); });
    const title = document.getElementById('nu-admin-title');
    if (title) title.textContent = current.querySelector('h1,h2')?.textContent || 'Administração';
    root.querySelectorAll('.sidebar a[href^="#"]').forEach(a => {
      a.classList.toggle('active', a.hash === '#' + current.id);
    });
  };
  window.addEventListener('hashchange', activate);
  activate();
})();
