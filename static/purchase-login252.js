(()=>{'use strict';
 const root=document.querySelector('[data-native-menu]');
 if(!root||root.dataset.loginRequired252!=='1')return;
 const url='/entrar?tipo=cliente&comprar=1';
 function login(){location.assign(url);}
 window.NOWUP_LOGIN252={login};
 const controls='[data-add],[data-login-buy252],.nu201-open,.nu190-add,.nu151-choose,[data-checkout],[data-dock-checkout],[data-cart-summary],.nu162-top-cart';
 document.addEventListener('click',e=>{const target=e.target.closest?.(controls);if(target&&root.contains(target)&&!target.disabled){e.preventDefault();e.stopImmediatePropagation();login();}},true);
 document.addEventListener('submit',e=>{if(e.target.matches('[data-order-form]')&&root.contains(e.target)){e.preventDefault();e.stopImmediatePropagation();login();}},true);
})();
