/* NowUp V98: navegação vertical instantânea; mantém carrosséis horizontais. */
(() => {
  'use strict';
  const instant = options => options && typeof options === 'object'
    ? {...options, behavior: 'instant'} : options;
  for (const name of ['scroll', 'scrollTo', 'scrollBy']) {
    const original = window[name];
    window[name] = function(...args) {
      if (args[0] && typeof args[0] === 'object') args[0] = instant(args[0]);
      return original.apply(window, args);
    };
  }
  const intoView = Element.prototype.scrollIntoView;
  Element.prototype.scrollIntoView = function(options) {
    return intoView.call(this, instant(options));
  };
  for (const name of ['scroll', 'scrollTo', 'scrollBy']) {
    const original = Element.prototype[name];
    if (!original) continue;
    Element.prototype[name] = function(...args) {
      const options = args[0];
      // Não modifica rolagens que especificam apenas deslocamento horizontal.
      if (options && typeof options === 'object' && 'top' in options) args[0] = instant(options);
      return original.apply(this, args);
    };
  }
  // Captura antes do script antigo que animava a volta ao topo.
  window.addEventListener('click', event => {
    const button = event.target instanceof Element && event.target.closest('[data-panel-back-top]');
    if (!button) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    window.scrollTo({top: 0, left: 0, behavior: 'instant'});
  }, true);
})();
