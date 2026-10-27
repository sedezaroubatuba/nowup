/* Loaded only after the server authenticates a matching successful-order cookie. */
(() => {
 const node=document.getElementById('cart-confirmation200');if(!node)return;
 try{
  const data=JSON.parse(node.textContent),path=data.path,id=Number(data.customerId);
  if(!path?.startsWith('/p/')||!Number.isSafeInteger(id)||id<1)return;
  const prefix='nowup-cart:u:'+id+':',info='nowup-cart-info:u:'+id+':';
  const submittedKey=prefix+path;
  let pending=null;try{pending=JSON.parse(sessionStorage.getItem('nowup-checkout247:'+submittedKey)||'null');}catch(_){}
  if(pending&&localStorage.getItem(submittedKey)!==pending.snapshot){
   sessionStorage.removeItem('nowup-checkout247:'+submittedKey);
   document.cookie='nowup_cart_completed=; Max-Age=0; Path=/; SameSite=Lax';return;
  }
  sessionStorage.removeItem('nowup-checkout247:'+submittedKey);
  for(const suffix of [path,path+'/menu']){localStorage.removeItem(prefix+suffix);localStorage.removeItem(info+suffix);}
  // Guest carts from the same store must not reappear after login/logout.
  for(const suffix of [path,path+'/menu']){localStorage.removeItem('nowup-cart:'+suffix);localStorage.removeItem('nowup-cart-info:'+suffix);}
  document.cookie='nowup_cart_completed=; Max-Age=0; Path=/; SameSite=Lax';
  window.dispatchEvent(new Event('nowup-cart-changed'));
 }catch(_){}
})();
