/* Delegation also handles store headers inserted after page initialization. */
document.addEventListener('click', event => {
  const button = event.target.closest('.nu232-info-toggle');
  if (!button) return;
  const information = button.closest('.nu187-intro')?.querySelector('.nu187-information');
  if (!information) return;
  information.open = !information.open;
  button.setAttribute('aria-expanded', String(information.open));
  button.textContent = information.open ? 'Ver menos ‹' : 'Ver mais ›';
});
/* Integrated store cover and one sticky search/categories/banner group. */
document.addEventListener('DOMContentLoaded', () => {
  'use strict';
  const root = document.querySelector('[data-native-menu]');
  const bar = root?.querySelector('.nu-menu-sticky');
  const intro = root?.querySelector('.nu187-intro');
  const nav = root?.querySelector('.menu-category-nav');
  if (!root || !bar || !intro) return;
  const mobile = matchMedia('(max-width:900px)');
  const body = document.body;
  let queued = false;
  function measure() {
    queued = false;
    const home = body.classList.contains('nu187-store-home');
    if (home) {
      const banner = root.querySelector('.nu207-banners');
      if (banner) {
        if (bar.nextElementSibling !== banner) bar.after(banner);
        banner.dataset.layout286='below-search';
        if (intro.nextElementSibling !== bar) bar.before(intro);
        if (nav && banner.nextElementSibling !== nav) banner.after(nav);
      } else {
        if (intro.nextElementSibling !== bar) bar.before(intro);
        if (nav && bar.nextElementSibling !== nav) bar.after(nav);
      }
    } else if (nav && nav.parentElement !== bar) bar.append(nav);
    // The slideshow belongs to the page flow, never the sticky search controls.
    body.classList.toggle('nu237-banner-hidden', !home);
    if (body.classList.contains('nu248-slide-collapsed')) body.classList.remove('nu248-slide-collapsed');
    const height = Math.ceil(bar.getBoundingClientRect().height);
    setSize('--nu232-sticky-height', height + 'px');
    const dock = root.querySelector('.nu83-cart-dock:not([hidden])');
    const dockHeight = dock && getComputedStyle(dock).position === 'fixed' && dock.getBoundingClientRect().height > 0 ? dock.getBoundingClientRect().height + 24 : 20;
    // Four complete cards (2x2), after the cover has scrolled out of view.
    const cardHeight = Math.max(150, Math.min(240, Math.floor((window.innerHeight - height - 44 - 32 - dockHeight - 8) / 2)));
    setSize('--nu232-card-height', cardHeight + 'px');
  }
  function setSize(name, value) {
    if (body.style.getPropertyValue(name) !== value) body.style.setProperty(name, value);
  }
  function schedule() {
    if (!queued) {queued = true; requestAnimationFrame(measure);}
  }
  function enable() {
    body.classList.add('nu233-store');
    body.classList.toggle('nu232-store', mobile.matches);
    body.classList.toggle('nu233-desktop', !mobile.matches);
    const cover = intro.querySelector('.nu187-cover');
    intro.classList.toggle('nu233-has-cover', !!cover?.style.backgroundImage && cover.style.backgroundImage !== 'none');
    schedule();
  }
  // Text, quantities and photo changes do not alter the sticky controls.
  new MutationObserver(records => {
    if (records.some(r => [...r.addedNodes, ...r.removedNodes].some(n =>
      n.nodeType === 1 && (n.matches('.nu207-banners,.nu83-cart-dock') || n.querySelector('.nu207-banners,.nu83-cart-dock'))))) schedule();
  }).observe(root, {childList: true, subtree: true});
  let homeState = body.classList.contains('nu187-store-home');
  new MutationObserver(() => {
    const home = body.classList.contains('nu187-store-home');
    if (home !== homeState) {homeState = home; schedule();}
  }).observe(body, {attributes: true, attributeFilter: ['class']});
  new ResizeObserver(schedule).observe(bar);
  window.addEventListener('resize', schedule, {passive: true});
  window.visualViewport?.addEventListener('resize', schedule, {passive: true});
  mobile.addEventListener('change', enable);
  window.addEventListener('nowup-cart-changed', schedule);
  window.addEventListener('nowup-slide-ready286', schedule);
  enable();
});

