/* V455: lightweight list interactions; every edit remains server-validated. */
(() => {
  "use strict";
  const root = document.querySelector(".nu455-root");
  if (!root) return;
  const normalize = value => String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
  let catalog = [];
  try { catalog = JSON.parse(document.getElementById("nu455-product-names")?.textContent || "[]"); } catch (_) {}
  const byId = new Map(catalog.map(p => [String(p.id), p.name]));
  root.querySelectorAll(".nu455-item").forEach(row => {
    row.addEventListener("toggle", () => {
      if (!row.open) return;
      root.querySelectorAll(".nu455-item[open]").forEach(other => { if (other !== row) other.open = false; });
    });
  });
  root.querySelectorAll("[data-category455]").forEach(select => {
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
  root.querySelectorAll("[data-related455]").forEach(buildPicker);
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
