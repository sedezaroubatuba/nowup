(() => {
  const root = document.querySelector('[data-vitrine]');
  if (!root) return;
  const customer = Number(root.dataset.customer);
  const dialog = document.getElementById('vitrine-login');
  const status = root.querySelector('[data-vitrine-status]');
  const pendingKey = 'nowup-vitrine-pending473';
  const slugPattern = /^[a-zA-Z0-9_-]+$/;
  const cartKey = slug => 'nowup-cart:u:' + customer + ':/p/' + slug;
  const menuUrl = slug => '/p/' + slug + '/menu';
  const entries = slug => new Map(JSON.parse(localStorage.getItem(cartKey(slug)) || '[]'));

  function refresh() {
    root.querySelectorAll('[data-vitrine-cart]').forEach(link => {
      let count = 0;
      try { count = [...entries(link.dataset.slug).values()].reduce((n, row) => n + Number(row.quantity || 0), 0); } catch (_) {}
      link.hidden = !customer || count < 1;
      link.querySelector('[data-vitrine-count]').textContent = String(count);
      link.setAttribute('aria-label', 'Carrinho, ' + count + (count === 1 ? ' item' : ' itens'));
    });
  }

  function add(item) {
    if (!item || !slugPattern.test(item.slug) || !Number.isSafeInteger(item.id) || item.id < 1) return;
    if (!customer) {
      try { sessionStorage.setItem(pendingKey, JSON.stringify({item, expires: Date.now()+30*60*1000})); } catch (_) {}
      dialog.showModal();
      return;
    }
    if (item.options) {
      location.assign(menuUrl(item.slug) + '?produto=' + item.id + '&vitrine_opcoes=1');
      return;
    }
    try {
      const cart = entries(item.slug);
      const id = item.id + '::utensils0:notes';
      const max = Math.max(1, Math.min(99, Number(item.max) || 99));
      const quantity = Number(cart.get(id)?.quantity || 0);
      if (quantity >= max) {
        status.textContent = 'Limite de unidades deste produto atingido.';
        return;
      }
      cart.set(id, {productId:item.id, name:item.name, unitPrice:item.price, quantity:quantity+1,
        notes:'', options:[], utensils:false, max});
      localStorage.setItem(cartKey(item.slug), JSON.stringify([...cart]));
      localStorage.setItem('nowup-cart-info:u:' + customer + ':/p/' + item.slug,
        JSON.stringify({name:item.store, updated:Date.now()}));
      status.textContent = item.name + ' adicionado ao carrinho.';
      refresh();
    } catch (_) {
      status.textContent = 'Não foi possível atualizar o carrinho. Tente novamente.';
    }
  }

  window.NowUpVitrine473 = {add};
  root.addEventListener('click', event => {
    const button = event.target.closest('[data-vitrine-item]');
    if (button) add(JSON.parse(button.dataset.vitrineItem));
    const cover = event.target.closest('[data-vitrine-category]');
    if (!cover) return;
    const selected = cover.getAttribute('aria-pressed') !== 'true';
    root.querySelectorAll('[data-vitrine-category]').forEach(other => {
      const active = selected && other === cover;
      other.setAttribute('aria-pressed', String(active));
      document.getElementById(other.getAttribute('aria-controls')).hidden = !active;
    });
    if (selected) document.getElementById(cover.getAttribute('aria-controls')).scrollIntoView({block:'start'});
  });

  dialog.querySelector('form').addEventListener('submit', () => {
    try { sessionStorage.removeItem(pendingKey); } catch (_) {}
  });
  dialog.addEventListener('cancel', () => {
    try { sessionStorage.removeItem(pendingKey); } catch (_) {}
  });
  if (customer) {
    try {
      const pending = JSON.parse(sessionStorage.getItem(pendingKey) || 'null');
      sessionStorage.removeItem(pendingKey);
      if (pending?.expires > Date.now()) add(pending.item);
    } catch (_) {}
  }
  window.addEventListener('pageshow', refresh);
  window.addEventListener('storage', refresh);
  refresh();
})();
