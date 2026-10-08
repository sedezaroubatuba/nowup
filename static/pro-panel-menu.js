(function () {
  function initProductFilters(dashboard) {
    const grid = dashboard.querySelector('[data-pro-products]');
    const nav = dashboard.querySelector('.pro-product-filters');
    if (!grid || !nav) return;
    const buttons = Array.from(nav.querySelectorAll('[data-pro-category]'));
    const normalize = value => String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim().replace(/\s+/g, ' ').toLowerCase();
    const empty = document.createElement('p');
    empty.className = 'muted full';
    empty.setAttribute('role', 'status');
    empty.textContent = 'Nenhum produto nesta categoria.';
    empty.style.gridColumn = '1 / -1';
    empty.hidden = true;
    grid.append(empty);
    function filter(button) {
      const selected = normalize(button.dataset.proCategory);
      let visibleCount = 0;
      grid.querySelectorAll('[data-pro-product]').forEach(card => {
        const visible = selected === 'all' || (selected === 'promocoes' ? card.dataset.featured === '1' : normalize(card.dataset.category) === selected);
        card.hidden = !visible;
        card.style.setProperty('display', visible ? 'block' : 'none', 'important');
        if (visible) visibleCount++;
      });
      buttons.forEach(item => {
        const active = item === button;
        item.classList.toggle('active', active);
        item.setAttribute('aria-pressed', String(active));
      });
      empty.hidden = visibleCount > 0;
      empty.style.setProperty('display', visibleCount ? 'none' : 'block', 'important');
    }
    dashboard.addEventListener('click', event => {
      const button = event.target.closest('[data-pro-category]');
      if (!button || !nav.contains(button)) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      filter(button);
    }, true);
    if (buttons.length) filter(buttons.find(button => button.classList.contains('active')) || buttons[0]);
  }

  function initPanelMenu() {
    const dashboard = document.querySelector('.pro-dashboard');
    if (!dashboard) return;
    initProductFilters(dashboard);

    const menuToggle = dashboard.querySelector('[data-pro-menu-toggle]');
    const sidebar = dashboard.querySelector('.pro-sidebar');
    const shade = dashboard.querySelector('[data-close-pro-menu]');

    const closeMenu = () => {
      dashboard.classList.remove('pro-menu-open');
      if (menuToggle) menuToggle.setAttribute('aria-expanded', 'false');
      if (shade) shade.hidden = true;
    };

    if (menuToggle && sidebar) {
      menuToggle.addEventListener('click', () => {
        const open = dashboard.classList.toggle('pro-menu-open');
        menuToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        if (shade) shade.hidden = !open;
      });
    }

    shade?.addEventListener('click', closeMenu);
    document.addEventListener('keydown', event => { if (event.key === 'Escape') closeMenu(); });

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
        event.preventDefault();
        reason?.focus();
        window.alert('Informe o motivo antes de cancelar ou recusar.');
        return;
      }
      const submit=form.querySelector('button:not([type="button"])');
      if(submit){submit.disabled=true;submit.textContent='Atualizando…';}
    }));

    dashboard.querySelectorAll('[data-print-order]').forEach(button => button.addEventListener('click', () => {
      const card = button.closest('.order-card');
      if (card) {
        card.classList.add('print-order-target');
        window.print();
        card.classList.remove('print-order-target');
      }
    }));

    const links=[...dashboard.querySelectorAll('.pro-sidebar a[href^="#"]')];
    const sections=[...dashboard.querySelectorAll('main > section')];
    const groups={
      hoje:['pedidos-ativos'],
      resumo:['resumo','estatisticas'],
      pedidos:['pedidos'],
      cardapio:['cardapio'],
      adicionais:['adicionais'],
      clientes:['clientes'],
      relatorios:['relatorios','mais-pedidos'],
      perfil:['perfil','identidade','fotos','publicidade'],
      horarios:['horarios','links'],
      publicar:['publicar'],
      notificacoes:['notificacoes']
    };

    function localDay(){
      const parts=new Intl.DateTimeFormat('en-US',{timeZone:'America/Sao_Paulo',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());
      const value=type=>parts.find(part=>part.type===type).value;
      return `${value('year')}-${value('month')}-${value('day')}`;
    }
    function dayChanged(){ return dashboard.dataset.panelDay && dashboard.dataset.panelDay!==localDay(); }
    window.setInterval(()=>{ const hash=location.hash.slice(1); if(!document.hidden && (!hash || hash==='hoje') && dayChanged()) location.replace('/painel'); },30000);
    function navigate(){
      const hash=location.hash.slice(1);
      let group=Object.keys(groups).find(key=>groups[key].includes(hash))||'hoje';
      if(/^pedido-\d+$/.test(hash))group='pedidos';
      if(group==='hoje' && dayChanged()){ location.replace('/painel'); return; }

      dashboard.classList.add('show-full-dashboard');
      sections.forEach(section=>{
        const visible=groups[group].includes(section.id);
        section.hidden=!visible;
        section.style.setProperty('display',visible?(section.id==='estatisticas'?'grid':'block'):'none','important');
      });
      dashboard.querySelectorAll('.v35-store-dashboard,[data-toggle-pro-dashboard]').forEach(el=>el.style.setProperty('display','none','important'));
      links.forEach(link=>{
        const active=link.hash==='#'+group;
        link.classList.toggle('active',active);
        if(active)link.setAttribute('aria-current','page'); else link.removeAttribute('aria-current');
      });
      closeMenu();

      requestAnimationFrame(()=>{
        if(/^pedido-\d+$/.test(hash)){
          const target=document.getElementById(hash);
          if(target){
            target.scrollIntoView({block:'start',behavior:'smooth'});
            target.classList.add('v61-order-focus');
            setTimeout(()=>target.classList.remove('v61-order-focus'),1800);
          }
        }else{
          window.scrollTo({top:0,behavior:'smooth'});
        }
      });
    }

    function openOrder(id){
      id=Number(id||0);
      if(!id)return;
      const hash=`#pedido-${id}`;
      const target=document.getElementById(`pedido-${id}`);
      if(!target){
        location.assign(`/painel?abrir_pedido=${id}&t=${Date.now()}${hash}`);
        return;
      }
      if(location.hash!==hash)history.pushState(null,'',hash);
      navigate();
    }

    dashboard.addEventListener('click',event=>{
      const orderLink=event.target.closest('[data-open-order]');
      if(orderLink){
        event.preventDefault();
        openOrder(orderLink.dataset.openOrder);
        return;
      }
      const notificationLink=event.target.closest('[data-notification-link]');
      if(notificationLink){
        const match=(notificationLink.getAttribute('href')||'').match(/#pedido-(\d+)/);
        if(match){event.preventDefault();openOrder(match[1]);}
      }
    });

    links.forEach(link=>link.addEventListener('click',()=>{
      if(location.hash===link.hash)navigate();
    }));
    window.addEventListener('hashchange',navigate);
    window.addEventListener('popstate',navigate);
    navigate();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPanelMenu);
  } else {
    initPanelMenu();
  }
})();
