/* Integrated store cover and one sticky search/categories/banner group. */
document.addEventListener('DOMContentLoaded', () => {
  'use strict';
  const root = document.querySelector('[data-native-menu]');
  const bar = root?.querySelector('.nu-menu-sticky');
  const intro = root?.querySelector('.nu187-intro');
  const nav = root?.querySelector('.menu-category-nav');
  if (!root || !bar || !intro) return;
  const infoButton = intro.querySelector('.nu232-info-toggle');
  const information = intro.querySelector('.nu187-information');
  infoButton?.addEventListener('click', () => {information.open = !information.open; infoButton.setAttribute('aria-expanded', String(information.open)); infoButton.textContent = information.open ? 'Ver menos ‹' : 'Ver mais ›';});
  const mobile = matchMedia('(max-width:900px)');
  const body = document.body;
  const slideToggle = document.createElement('button');
  slideToggle.type = 'button';
  slideToggle.className = 'nu248-slide-toggle';
  slideToggle.hidden = true;
  let slideCollapsed = false;
  slideToggle.addEventListener('click', () => {
    slideCollapsed = !slideCollapsed;
    measure();
  });
  let queued = false;
  function measure() {
    queued = false;
    const home = body.classList.contains('nu187-store-home');
    if (home) {
      if (bar.previousElementSibling !== intro) bar.before(intro);
      if (nav && nav.parentElement !== bar) bar.append(nav);
      const banner = root.querySelector('.nu207-banners');
      if (slideToggle.parentElement !== bar || (nav && slideToggle.nextElementSibling !== nav)) bar.insertBefore(slideToggle, nav || null);
      if (banner && (banner.parentElement !== bar || banner.nextElementSibling !== slideToggle)) bar.insertBefore(banner, slideToggle);
    }
    const banner = root.querySelector('.nu207-banners');
    // On desktop the whole shopping header scrolls naturally. On mobile keep
    // the current sticky group, with an explicit control to reclaim its space.
    const beforeCover = intro.getBoundingClientRect().bottom > 1;
    const bannerHidden = !home || (mobile.matches && (beforeCover || slideCollapsed));
    if (body.classList.contains('nu237-banner-hidden') !== bannerHidden) body.classList.toggle('nu237-banner-hidden', bannerHidden);
    body.classList.toggle('nu248-slide-collapsed', mobile.matches && slideCollapsed);
    slideToggle.hidden = !mobile.matches || !home || !banner || beforeCover;
    const toggleLabel = slideCollapsed ? 'Mostrar slide ↓' : 'Subir slide ↑';
    if (slideToggle.textContent !== toggleLabel) slideToggle.textContent = toggleLabel;
    slideToggle.setAttribute('aria-expanded', String(!slideCollapsed));
    if (banner) {
      banner.id = 'nu248-store-slides';
      slideToggle.setAttribute('aria-controls', banner.id);
    }
    const height = Math.ceil(bar.getBoundingClientRect().height);
    body.style.setProperty('--nu232-sticky-height', height + 'px');
    const dock = root.querySelector('.nu83-cart-dock:not([hidden])');
    const dockHeight = dock && getComputedStyle(dock).position === 'fixed' && dock.getBoundingClientRect().height > 0 ? dock.getBoundingClientRect().height + 24 : 20;
    // Four complete cards (2x2), after the cover has scrolled out of view.
    const cardHeight = Math.max(150, Math.min(240, Math.floor((window.innerHeight - height - 44 - 32 - dockHeight - 8) / 2)));
    body.style.setProperty('--nu232-card-height', cardHeight + 'px');
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
  new MutationObserver(schedule).observe(root, {childList: true, subtree: true});
  new MutationObserver(schedule).observe(body, {attributes: true, attributeFilter: ['class']});
  new ResizeObserver(schedule).observe(bar);
  window.addEventListener('scroll', schedule, {passive: true});
  window.addEventListener('resize', schedule, {passive: true});
  window.visualViewport?.addEventListener('resize', schedule, {passive: true});
  mobile.addEventListener('change', enable);
  window.addEventListener('nowup-cart-changed', schedule);
  enable();
});
