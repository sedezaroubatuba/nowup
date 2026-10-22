/* Refresh only the board. Product editors and the current order conversation stay intact. */
(() => {
  'use strict';
  const root=document.querySelector('[data-merchant228]');
  if(!root)return;
  const host=root.querySelector('[data-board228]'),room=root.querySelector('#pedidos-ativos');
  const search=root.querySelector('[data-search-input228]'),message=root.querySelector('[data-live228]');
  const mobile=matchMedia('(max-width:900px)');
  let selected='new',busy=false,pending=false,timer;
  const normalize=value=>String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  const announce=(text,error=false)=>{message.textContent=text;message.toggleAttribute('data-error',error);};
  function filter(){
    const query=normalize(search.value.trim());
    host.querySelectorAll('[data-column228]').forEach(column=>{
      let visible=0;
      column.querySelectorAll('[data-card228]').forEach(card=>{
        card.hidden=!normalize(card.dataset.search228).includes(query);
        if(!card.hidden)visible++;
      });
      column.querySelector('.mk228-no-match').hidden=!query||visible>0||!column.querySelector('[data-card228]');
      const empty=column.querySelector('.mk228-empty');if(empty)empty.hidden=!!query;
    });
  }
  function select(key,focus=false){
    selected=key;
    const tabs=[...host.querySelectorAll('[data-stage228]')];
    tabs.forEach(tab=>{const active=tab.dataset.stage228===selected;tab.setAttribute('aria-selected',String(active));tab.tabIndex=mobile.matches?(active?0:-1):0;});
    host.querySelectorAll('[data-column228]').forEach(column=>{
      column.hidden=mobile.matches&&column.dataset.column228!==selected;
      if(mobile.matches)column.setAttribute('role','tabpanel');else column.removeAttribute('role');
    });
    if(focus)tabs.find(tab=>tab.dataset.stage228===selected)?.focus();
  }
  function usableBoard(){return !room.hidden&&getComputedStyle(room).display!=='none';}
  async function refresh(manual=false){
    if(busy||pending||(!manual&&(document.hidden||!usableBoard())))return;
    // Do not remove a card while the merchant is selecting or submitting an action.
    if(!manual&&host.contains(document.activeElement)&&document.activeElement.closest('[data-change228]'))return;
    busy=true;
    const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),10000);
    try{
      const response=await fetch('/painel/kanban228',{credentials:'same-origin',cache:'no-store',signal:controller.signal});
      if(response.status===401||response.status===403){announce('Sua sessão terminou. Entre novamente para atualizar os pedidos.',true);clearInterval(timer);return;}
      if(!response.ok||response.redirected)throw Error('Não foi possível atualizar.');
      const html=await response.text();
      const doc=new DOMParser().parseFromString(html,'text/html');
      if(!doc.querySelector('.mk228-board'))throw Error('Entre novamente para atualizar os pedidos.');
      const focus=document.activeElement?.dataset?.stage228;
      // Server-rendered, escaped merchant data, from this application's authenticated endpoint.
      host.replaceChildren(...doc.body.childNodes);
      select(selected);filter();
      if(focus)host.querySelector('[data-stage228="'+focus+'"]')?.focus();
      announce('Atualizado às '+new Intl.DateTimeFormat('pt-BR',{hour:'2-digit',minute:'2-digit',second:'2-digit'}).format(new Date())+' • atualização automática.');
    }catch(_){announce('Não foi possível atualizar. Confira sua conexão e toque em Atualizar.',true);}
    finally{clearTimeout(timeout);busy=false;}
  }
  root.querySelector('[data-refresh228]').addEventListener('click',()=>refresh(true));
  search.addEventListener('input',filter);
  host.addEventListener('click',event=>{const tab=event.target.closest('[data-stage228]');if(tab)select(tab.dataset.stage228);});
  host.addEventListener('keydown',event=>{
    const tab=event.target.closest('[data-stage228]');if(!tab||!['ArrowRight','ArrowLeft','Home','End'].includes(event.key))return;
    event.preventDefault();const keys=[...host.querySelectorAll('[data-stage228]')].map(tab=>tab.dataset.stage228),index=keys.indexOf(selected);
    select(event.key==='Home'?keys[0]:event.key==='End'?keys.at(-1):keys[(index+(event.key==='ArrowRight'?1:-1)+keys.length)%keys.length],true);
  });
  host.addEventListener('submit',async event=>{
    const form=event.target.closest('[data-change228]');if(!form)return;
    event.preventDefault();if(pending||busy)return;
    pending=true;const button=form.querySelector('button'),label=button.textContent;
    button.disabled=true;button.textContent='Salvando…';
    const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),15000);
    try{
      const response=await fetch(form.action,{method:'POST',credentials:'same-origin',body:new FormData(form),signal:controller.signal});
      const url=new URL(response.url);
      if(!response.ok){let detail='Não foi possível salvar o status.';try{detail=(await response.json()).detail||detail;}catch(_){}throw Error(detail);}
      if(url.pathname==='/entrar')throw Error('Sua sessão terminou. Entre novamente.');
      if(url.searchParams.has('erro'))throw Error('O pedido mudou ou esta ação não é permitida. Atualize e confira os itens.');
      if(url.pathname!=='/painel'||url.searchParams.get('ok')!=='pedido')throw Error('Confira o pedido antes de continuar.');
      pending=false;await refresh(true);
    }catch(error){announce(error.name==='AbortError'?'Não foi possível confirmar o resultado. Atualize o quadro antes de tentar novamente.':error.message,true);}
    finally{clearTimeout(timeout);pending=false;if(button.isConnected){button.disabled=false;button.textContent=label;}}
  });
  // Reuse the original sound control and listener; never announce activation before user consent.
  const alerts=document.querySelector('[data-order-alerts]');
  if(alerts)room.querySelector('.mk228-heading').after(alerts);
  const originalClose=root.querySelector('[data-close-pro-menu].btn');if(originalClose)originalClose.textContent='✕ Fechar';
  const toggle=root.querySelector('[data-pro-menu-toggle]'),sidebar=root.querySelector('.pro-sidebar');
  let wasOpen=false;
  const syncMenu=()=>{
    const open=root.classList.contains('nu198-menu-open');
    document.body.classList.toggle('mk228-menu-open',open&&mobile.matches);
    if(open&&!wasOpen)sidebar.querySelector('[data-close-pro-menu]')?.focus();
    if(!open&&wasOpen&&mobile.matches)toggle?.focus();
    wasOpen=open;
  };
  new MutationObserver(syncMenu).observe(root,{attributes:true,attributeFilter:['class']});
  root.addEventListener('keydown',event=>{
    if(event.key!=='Tab'||!mobile.matches||!root.classList.contains('nu198-menu-open'))return;
    const controls=[...sidebar.querySelectorAll('a,button,input')].filter(el=>el.getClientRects().length&&!el.disabled);
    const first=controls[0],last=controls.at(-1);
    if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus();}
    else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus();}
  });
  mobile.addEventListener('change',()=>{select(selected);syncMenu();});
  window.addEventListener('online',()=>refresh());
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh();});
  window.addEventListener('hashchange',()=>{if(usableBoard())refresh();});
  select(selected);filter();timer=setInterval(()=>refresh(),10000);
})();
