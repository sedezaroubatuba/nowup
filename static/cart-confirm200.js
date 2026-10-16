/* Loaded only after the server authenticates a matching successful-order cookie. */
(() => {
 const node=document.getElementById('cart-confirmation200');if(!node)return;
 try{
  const data=JSON.parse(node.textContent),path=data.path,id=Number(data.customerId);
  if(!path?.startsWith('/p/')||!Number.isSafeInteger(id)||id<1)return;
  const prefix='nowup-cart:u:'+id+':',info='nowup-cart-info:u:'+id+':';
  for(const suffix of [path,path+'/menu']){localStorage.removeItem(prefix+suffix);localStorage.removeItem(info+suffix);}
  // Guest carts from the same store must not reappear after login/logout.
  for(const suffix of [path,path+'/menu']){localStorage.removeItem('nowup-cart:'+suffix);localStorage.removeItem('nowup-cart-info:'+suffix);}
  window.dispatchEvent(new Event('nowup-cart-changed'));
 }catch(_){}
})();
