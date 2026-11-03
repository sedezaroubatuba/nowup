/* Autofill may fill credentials, but only an explicit button activation signs in. */
(() => {
  'use strict';
  const form = document.getElementById('nowup-login-form349');
  const button = document.getElementById('nowup-login-confirm349');
  if (!form || !button) return;
  let confirmed = false;
  form.addEventListener('submit', event => {
    if (!confirmed) event.preventDefault();
  });
  form.addEventListener('keydown', event => {
    if (event.key !== 'Enter' || event.isComposing || event.target.tagName !== 'INPUT') return;
    event.preventDefault();
    if (event.target.name === 'email') form.elements.password.focus();
    else button.focus();
  });
  button.addEventListener('click', event => {
    if (!event.isTrusted) return;
    confirmed = true;
    try { form.requestSubmit(); }
    finally { confirmed = false; }
  });
})();
