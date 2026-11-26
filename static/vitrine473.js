(() => {
  const root = document.querySelector('[data-vitrine]');
  if (!root) return;
  const customer = Number(root.dataset.customer);
  const status = root.querySelector('[data-vitrine-status]');
  const slugPattern = /^[a-zA-Z0-9_-]+$/;
  const storage = customer ? localStorage : sessionStorage;
  const cartKey = slug => 'nowup-cart:' + (customer ? 'u:' + customer + ':' : '') + '/p/' + slug;
  const menuUrl = slug => '/p/' + slug + '/menu';
  const entries = slug => new Map(JSON.parse(storage.getItem(cartKey(slug)) || '[]'));

  function refresh() {
    root.querySelectorAll('[data-vitrine-cart]').forEach(link => {
      let count = 0;
      try { count = [...entries(link.dataset.slug).values()].reduce((n, row) => n + Number(row.quantity || 0), 0); } catch (_) {}
      link.hidden = count < 1;
      link.querySelector('[data-vitrine-count]').textContent = String(count);
      link.setAttribute('aria-label', 'Carrinho, ' + count + (count === 1 ? ' item' : ' itens'));
    });
  }

  function add(item) {
    if (!item || !slugPattern.test(item.slug) || !Number.isSafeInteger(item.id) || item.id < 1) return;
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
      storage.setItem(cartKey(item.slug), JSON.stringify([...cart]));
      if (customer) localStorage.setItem('nowup-cart-info:u:' + customer + ':/p/' + item.slug,
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
  });

  window.addEventListener('pageshow', refresh);
  window.addEventListener('storage', refresh);
  refresh();
})();
