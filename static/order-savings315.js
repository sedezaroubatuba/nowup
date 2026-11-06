/* Compare each cart line once; delivery and paid extras are not discounts. */
(() => {
  'use strict';
  function calculate(lines, root) {
    let total = 0;
    for (const line of lines) {
      const card = [...root.querySelectorAll('[data-product]')].find(c => Number(c.dataset.id) === Number(line.productId));
      if (!card) continue;
      const price = Number(card.dataset.price), regular = Number(card.dataset.regular256);
      if(line.weightGrams370){
        if(Number.isSafeInteger(line.weightGrams370)&&line.weightGrams370>=100&&line.weightGrams370<=99900&&line.weightGrams370%100===0&&Number.isSafeInteger(price)&&Number.isSafeInteger(regular)&&line.unitPrice===Math.floor((price*line.weightGrams370+500)/1000))total+=Math.max(0,Math.floor((regular*line.weightGrams370+500)/1000)-line.unitPrice);
        continue;
      }
      const extras = (line.options || []).reduce((sum, option) => sum + Number(option.price || 0), 0);
      const count = Number(line.quantity);
      if (![price, regular, extras, line.unitPrice, count].every(Number.isSafeInteger) || price < 0 || extras < 0 || count < 1 || count > 99 || line.unitPrice !== price + extras) continue;
      let reference = Math.max(price, regular);
      if (card.dataset.combo256 === '1' && window.NOWUP_COMBO_PRICE303) {
        try {
          const value = window.NOWUP_COMBO_PRICE303.compare(JSON.parse(card.dataset.custom192 || '{}'), JSON.parse(card.dataset.comboPrices303 || '{}'), price, line.customization?.groups || {});
          if (value && !value.variable) reference = Math.max(reference, value.separate);
        } catch (_) { /* Missing comparison data must never invent savings. */ }
      }
      total += Math.max(0, reference - price) * count;
    }
    return total;
  }
  function render(lines, root, dialog) {
    const cents = calculate(lines, root);
    for (const target of [root.querySelector('[data-cart-total]'), dialog.querySelector('[data-dialog-total]')]) {
      if (!target) continue;
      const container = target.closest('.menu-cart,form') || target.parentElement;
      let notice = container.querySelector('[data-order-savings315]');
      if (!notice) {
        notice = document.createElement('p');
        notice.dataset.orderSavings315 = '';
        notice.setAttribute('role', 'status');
        notice.style.cssText = 'padding:12px 14px;border:1px solid #ddc9f4;border-radius:12px;background:#f5effc;color:#6026a0;font-weight:700;line-height:1.5';
        target.parentElement.after(notice);
      }
      notice.hidden = cents <= 0;
      notice.textContent = cents > 0 ? '🎉 Você está economizando ' + (cents / 100).toLocaleString('pt-BR', {style:'currency',currency:'BRL'}) + ' neste pedido!' : '';
    }
  }
  window.NOWUP_SAVINGS315 = {calculate, render};
})();
