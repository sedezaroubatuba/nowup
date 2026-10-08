(() => {
  document.querySelectorAll('[data-saved-address]').forEach(root => {
    const form = root.querySelector('[data-address-editor]');
    const toggle = root.querySelector('[data-change-address]');
    if (!form || !toggle) return;
    toggle.addEventListener('click', () => { form.hidden = false; toggle.hidden = true; form.querySelector('[name="address"]').focus(); });
    root.querySelector('[data-cancel-address]').addEventListener('click', () => { form.reset(); form.hidden = true; toggle.hidden = false; });
  });
  document.querySelectorAll('[data-checkout-change-address]').forEach(button => button.addEventListener('click', () => {
    const root = button.closest('[data-address]');
    root.querySelectorAll('[data-checkout-address]').forEach(input => { input.readOnly = false; });
    root.querySelector('[name="address"]').focus();
    button.hidden = true;
  }));
})();
