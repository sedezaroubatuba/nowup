(() => {
  'use strict';
  const root = document.querySelector('[data-native-menu] .menu-products');
  if (!root || root.dataset.categoryRows) return;
  const products = [...root.querySelectorAll('[data-product]')];
  if (!products.length) return;
  root.dataset.categoryRows = '1';
  const groups = new Map();
  for (const card of products) {
    const key = card.dataset.category || '';
    let group = groups.get(key);
    if (!group) {
      const section = document.createElement('section');
      section.className = 'nu-category-section';
      const header = document.createElement('header');
      const title = document.createElement('h3');
      title.textContent = card.querySelector('.menu-product-info > small')?.textContent.trim() || 'Outros produtos';
      const controls = document.createElement('div');
      controls.className = 'nu-category-arrows';
      const track = document.createElement('div');
      track.className = 'nu-category-track';
      track.tabIndex = 0;
      track.setAttribute('aria-label', title.textContent + ': produtos, deslize para os lados');
      for (const [label, symbol, direction] of [['Produtos anteriores', '‹', -1], ['Próximos produtos', '›', 1]]) {
        const button = document.createElement('button');
        button.type = 'button'; button.textContent = symbol;
        button.setAttribute('aria-label', label + ' em ' + title.textContent);
        button.onclick = () => track.scrollBy({left: direction * track.clientWidth * .85, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
        controls.append(button);
      }
      header.append(title, controls);
      const hint = document.createElement('small');
      hint.className = 'nu-category-hint'; hint.textContent = 'Deslize para ver mais →';
      section.append(header, hint, track); root.append(section);
      group = {section, track, cards: []}; groups.set(key, group);
    }
    // Move os mesmos elementos: mantém campos, dados e eventos do carrinho.
    group.track.append(card); group.cards.push(card);
  }
  function updateGroups() {
    for (const {section, cards} of groups.values()) {
      section.hidden = !cards.some(card => !card.hidden && getComputedStyle(card).display !== 'none');
    }
  }
  const observer = new MutationObserver(updateGroups);
  for (const card of products) observer.observe(card, {attributes: true, attributeFilter: ['hidden', 'style', 'class']});
  updateGroups();
})();
