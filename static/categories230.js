/* Shared category icons: local artwork, automatic names and a searchable picker. */
(() => {
  'use strict';
  const data = JSON.parse(document.getElementById('nu230-data')?.textContent || '{}');
  const catalog = data.catalog || [];
  const byKey = new Map(catalog.map(item => [item.key, item]));
  const normalize = value => String(value || '').normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  function resolve(name, chosen) {
    chosen = chosen || data.choices?.[normalize(name)];
    if (byKey.has(chosen)) return chosen;
    const text = ' ' + normalize(name) + ' ';
    return catalog.find(item => item.aliases.some(alias => text.includes(' ' + normalize(alias) + ' ')))?.key || 'grid';
  }
  function create(name, chosen) {
    const span = document.createElement('span');
    span.className = 'nu230-icon';
    span.setAttribute('aria-hidden', 'true');
    if (!chosen && ['promocoes', 'promocao'].includes(normalize(name))) {
      span.textContent = '🔥';
      return span;
    }
    const item = byKey.get(resolve(name, chosen));
    // Only bundled catalog SVG is inserted; category names are always textContent.
    if (item) span.innerHTML = '<svg class="nu230-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" focusable="false">' + item.svg + '</svg>';
    return span;
  }
  window.NowUpCategory230 = {create, resolve, normalize};
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.menu-category-nav [data-category-filter], .nu168-categories nav button').forEach(button => {
      const name = button.textContent.trim();
      const label = document.createElement('span'); label.className = 'nu230-label'; label.textContent = name;
      button.replaceChildren(create(name), label);
      if (button.closest('.nu168-categories')) {
        const arrow = document.createElement('span'); arrow.className = 'nu230-chevron'; arrow.textContent = '›'; arrow.setAttribute('aria-hidden', 'true'); button.append(arrow);
      }
    });
    const header = document.querySelector('.nu168-categories header');
    if (header) {
      const title = header.querySelector('h2');
      const group = document.createElement('div');
      const brand = document.createElement('span'); brand.className = 'nu230-brand'; brand.textContent = 'NowUp';
      title.before(group); group.append(brand, title);
    }
    document.querySelectorAll('[data-icon-picker230]').forEach(attachPicker);
  });
  function attachPicker(select) {
    const form = select.closest('form');
    const nameField = form?.querySelector('[name="name"]');
    if (!form || !nameField || !catalog.length) return;
    const button = document.createElement('button'); button.type = 'button'; button.className = 'nu230-preview';
    button.setAttribute('aria-haspopup', 'dialog');
    select.after(button); select.hidden = true;
    const hint = document.createElement('small'); hint.textContent = 'Escolhido pelo nome. Você pode trocar na galeria.'; button.after(hint);
    function refresh() {
      const key = resolve(nameField.value, select.value);
      const text = document.createElement('span');
      text.textContent = (select.value === 'auto' ? 'Automático: ' : '') + (byKey.get(key)?.label || 'Geral') + ' · Trocar ícone';
      button.replaceChildren(create(nameField.value, select.value), text);
      hint.textContent = select.value === 'auto' ? 'O ícone acompanha o nome da categoria.' : 'Ícone escolhido por você. Vale em todas as telas da loja.';
    }
    nameField.addEventListener('input', refresh); select.addEventListener('change', refresh); refresh();
    let dialog;
    button.addEventListener('click', () => {
      if (!dialog) dialog = buildGallery(select, nameField, button, refresh);
      dialog.showModal(); dialog.querySelector('input').value = ''; dialog.dispatchEvent(new Event('nu230refresh')); dialog.querySelector('input').focus();
    });
  }
  function buildGallery(select, nameField, opener, refresh) {
    const dialog = document.createElement('dialog'); dialog.className = 'nu230-gallery'; dialog.setAttribute('aria-label', 'Galeria de ícones da categoria');
    const header = document.createElement('header');
    const title = document.createElement('h2'); title.textContent = 'Escolha o ícone';
    const close = document.createElement('button'); close.type = 'button'; close.textContent = '×'; close.className = 'nu230-close'; close.setAttribute('aria-label', 'Fechar galeria'); close.onclick = () => dialog.close(); header.append(title, close);
    const search = document.createElement('input'); search.type = 'search'; search.placeholder = 'Buscar: cerveja, pizza, pet…'; search.setAttribute('aria-label', 'Buscar ícones');
    const automatic = document.createElement('button'); automatic.type = 'button'; automatic.className = 'nu230-auto'; automatic.textContent = 'Usar ícone automático pelo nome';
    const grid = document.createElement('div'); grid.className = 'nu230-icon-grid';
    const status = document.createElement('p'); status.setAttribute('role', 'status'); status.setAttribute('aria-live', 'polite');
    function choose(value) {select.value = value; select.dispatchEvent(new Event('change', {bubbles: true})); refresh(); dialog.close();}
    automatic.onclick = () => choose('auto');
    const entries = catalog.map(item => {
      const button = document.createElement('button'); button.type = 'button';
      const label = document.createElement('span'); label.textContent = item.label;
      button.append(create('', item.key), label); button.setAttribute('aria-label', item.label); button.onclick = () => choose(item.key); grid.append(button);
      return {item, button};
    });
    function filter() {
      const terms = normalize(search.value).split(' ').filter(Boolean); let count = 0;
      entries.forEach(({item, button}) => {button.hidden = !terms.every(term => normalize(item.label + ' ' + item.aliases.join(' ')).includes(term)); if (!button.hidden) count++; button.setAttribute('aria-pressed', String(select.value === item.key));});
      automatic.setAttribute('aria-pressed', String(select.value === 'auto'));
      status.textContent = count ? (count === 1 ? '1 ícone disponível' : count + ' ícones disponíveis') : 'Nenhum ícone encontrado. Você pode usar o automático.';
    }
    search.addEventListener('input', filter); dialog.addEventListener('nu230refresh', filter);
    dialog.addEventListener('close', () => opener.focus());
    dialog.addEventListener('click', event => {if (event.target !== dialog) return; const r = dialog.getBoundingClientRect(); if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) dialog.close();});
    dialog.append(header, search, automatic, status, grid); document.body.append(dialog); filter(); return dialog;
  }
})();
