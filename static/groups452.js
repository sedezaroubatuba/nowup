/* V452 — second preview: reveal four clean stacked flavors, with a show-all option.
   Does not alter cart IDs, prices, availability, or variant choice behavior. */
(() => {
  const setup = () => {
    document.querySelectorAll('[data-native-menu] .nu-group260[data-group260="1"]').forEach(group => {
      if (group.dataset.layout452 === 'ready') return;
      group.dataset.layout452 = 'ready';
      const list = group.querySelector(':scope > .nu-group260-items');
      if (!list) return;
      const rows = [...list.children].filter(el => el.matches('.nu-group260-row'));
      if (rows.length <= 4) return;
      const more = document.createElement('button');
      more.type = 'button';
      more.className = 'nu452-show-more';
      more.setAttribute('aria-expanded','false');
      const extraId = 'nu452-extra-'+String(group.dataset.id||Math.random().toString(36).slice(2));
      rows.slice(4).forEach((row,idx) => {if (!idx) row.id = extraId;});
      more.setAttribute('aria-controls', extraId);
      list.append(more);
      let all = false;
      const update = () => {
        rows.slice(4).forEach(row => {row.hidden = !all;});
        more.textContent = all ? 'Ver menos opções ↑' : 'Ver todas as '+rows.length+' opções ↓';
        more.setAttribute('aria-expanded', String(all));
      };
      more.addEventListener('click', () => {
        all = !all;
        update();
        if (!all) group.querySelector('.nu452-list-title')?.scrollIntoView({block:'nearest',behavior:'smooth'});
      });
      group.addEventListener('toggle', () => {
        if (!group.open && all) {all = false; update();}
      });
      update();
    });
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', setup, {once:true});
  else setup();
})();
