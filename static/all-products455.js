/* V455: lightweight list interactions; every edit remains server-validated. */
(() => {
  "use strict";
  const root = document.querySelector(".nu455-root");
  if (!root) return;
  const normalize = value => String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
  let catalog = [];
  try { catalog = JSON.parse(document.getElementById("nu455-product-names")?.textContent || "[]"); } catch (_) {}
  const byId = new Map(catalog.map(p => [String(p.id), p.name]));
  const list = root.querySelector(".nu455-list");
  // Keep the item count compact but continue down naturally: fetch 10 more
  // when the bottom sentinel approaches. Pagination links remain as fallback.
  root.addEventListener("toggle", event => {
    const row=event.target;
    if (!row.matches?.(".nu455-item") || !row.open)return;
    root.querySelectorAll(".nu455-item[open]").forEach(other=>{if(other!==row)other.open=false;});
  }, true);
  function initSubcategories(scope) {
   scope.querySelectorAll("[data-category455]").forEach(select => {
    if(select.dataset.initialized456)return;
    select.dataset.initialized456="1";
    const form = select.closest("form");
    const sub = form?.querySelector("[data-subcategory455]");
    if (!sub) return;
    function sync() {
      let selected = sub.value;
      let available = false;
      Array.from(sub.options).forEach(opt => {
        if (!opt.value) return;
        const match = normalize(opt.dataset.parent) === normalize(select.value);
        opt.hidden = !match;
        opt.disabled = !match;
        if (opt.value === selected && match) available = true;
      });
      if (!available) sub.value = "0";
    }
    select.addEventListener("change", sync);
    sync();
   });
  }
  initSubcategories(root);
  function buildPicker(host) {
    const self = String(host.dataset.self);
    const chosen = host.querySelector("[data-selected455]");
    const search = host.querySelector("[data-search455]");
    const results = host.querySelector("[data-results455]");
    const max = Math.min(20, Math.max(1, Number(host.dataset.max) || 20));
    if (!chosen || !search || !results) return;
    const selected = () => [...chosen.querySelectorAll('input[name="related256"]')].map(i => String(i.value));
    let chipZone = document.createElement("div");
    chipZone.className = "nu455-selected-chips";
    chosen.after(chipZone);
    function redrawChips() {
      chipZone.replaceChildren();
      selected().forEach(id => {
        const chip = document.createElement("span"), button = document.createElement("button");
        chip.className = "nu455-selected-chip";
        chip.textContent = byId.get(id) || ("Produto " + id);
        button.type = "button";
        button.textContent = "×";
        button.setAttribute("aria-label", "Remover sugestão " + (byId.get(id) || id));
        button.addEventListener("click", () => {
          chosen.querySelectorAll('input[name="related256"]').forEach(input => {
            if (input.value === id) input.remove();
          });
          redrawChips(); redrawResults();
        });
        chip.append(button); chipZone.append(chip);
      });
    }
    function redrawResults() {
      results.replaceChildren();
      const query = normalize(search.value);
      if (!query) return;
      const ids = new Set(selected());
      const found = catalog.filter(p => String(p.id) !== self &&
         !ids.has(String(p.id)) && normalize(p.name).includes(query)).slice(0,12);
      const limit = ids.size >= max;
      for (const item of found) {
        const button = document.createElement("button");
        button.type = "button"; button.textContent = "+ " + item.name;
        button.disabled = limit;
        button.addEventListener("click", () => {
          if (selected().length >= max || selected().includes(String(item.id))) return;
          const input = document.createElement("input");
          input.type = "hidden"; input.name = "related256"; input.value = item.id;
          chosen.append(input); search.value = ""; redrawChips(); redrawResults();
        });
        results.append(button);
      }
      if (!found.length) {
        const info = document.createElement("small");
        info.textContent = limit ? "Limite de 20 sugestões." : "Nenhum produto encontrado.";
        results.append(info);
      }
    }
    search.addEventListener("input", redrawResults);
    redrawChips();
  }
  function initPickers(scope){
    scope.querySelectorAll("[data-related455]").forEach(host=>{
      if(host.dataset.initialized456)return;
      host.dataset.initialized456="1";buildPicker(host);
    });
  }
  initPickers(root);
  const nav=root.querySelector(".nu455-pagination");
  const nextLink=()=>nav?.querySelector('a[href*="page="]:last-of-type');
  const sentinel=document.createElement("div");
  sentinel.className="nu456-load-sentinel";
  sentinel.setAttribute("role","status");
  sentinel.setAttribute("aria-live","polite");
  if(nav&&list&&window.IntersectionObserver){
    nav.after(sentinel);nav.classList.add("nu456-auto-pagination");
    let loading=false;
    const observer=new IntersectionObserver(async entries=>{
      if(!entries.some(e=>e.isIntersecting)||loading)return;
      const link=nav.querySelector('a[href*="page="]');
      const links=[...nav.querySelectorAll('a[href*="page="]')];
      const href=links.find(a=>a.textContent.includes("Próxima"))?.href;
      if(!href){sentinel.textContent="Fim dos produtos.";observer.disconnect();return;}
      loading=true;sentinel.textContent="Carregando mais produtos…";
      try{
        const res=await fetch(href,{credentials:"same-origin",cache:"no-store",headers:{"Accept":"text/html"}});
        if(!res.ok)throw Error("Falha ao carregar.");
        const doc=new DOMParser().parseFromString(await res.text(),"text/html");
        const newRows=[...doc.querySelectorAll(".nu455-list > .nu455-item")];
        if(!newRows.length){observer.disconnect();sentinel.textContent="Fim dos produtos.";return;}
        newRows.forEach(row=>list.append(document.importNode(row,true)));
        initSubcategories(list);initPickers(list);
        const newNav=doc.querySelector(".nu455-pagination");
        if(newNav)nav.replaceChildren(...[...newNav.childNodes].map(n=>document.importNode(n,true)));
        if(![...nav.querySelectorAll("a")].some(a=>a.textContent.includes("Próxima"))){
          sentinel.textContent="Todos os produtos carregados.";observer.disconnect();
        }else sentinel.textContent="";
      }catch(error){
        sentinel.textContent="Não foi possível carregar mais. Use o botão de próxima página.";
        nav.classList.remove("nu456-auto-pagination");observer.disconnect();
      }finally{loading=false;}
    },{rootMargin:"450px 0px"});
    observer.observe(sentinel);
  }
  root.querySelectorAll(".nu455-filters select").forEach(select =>
    select.addEventListener("change", () => select.form.requestSubmit())
  );
  root.querySelectorAll("[data-bulk-confirm455]").forEach(button => {
    const form = button.form;
    if (!form) return;
    form.addEventListener("submit", async event => {
      if (form.dataset.approved455 === "true") { form.dataset.approved455 = ""; return; }
      event.preventDefault();
      if (!form.reportValidity()) return;
      const cat = form.querySelector('select[name="category"]')?.value;
      const product = form.querySelector('select[name="target_id"]')?.selectedOptions[0]?.textContent;
      const message = "Associar " + product + " aos produtos da categoria " + cat +
        "? Essa sugestão aparecerá no Leve Junto dos produtos elegíveis.";
      let result;
      if (window.NowUpDialog?.confirm) result = await window.NowUpDialog.confirm(message);
      else result = window.confirm(message);
      if (result) {
        form.dataset.approved455 = "true";
        form.requestSubmit(button);
      }
    });
  });
})();
