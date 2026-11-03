(()=>{
  const prefix='nu333-test:';
  for(const name of ['localStorage','sessionStorage']){
    const raw=window[name];
    const keys=()=>Object.keys(raw).filter(k=>k.startsWith(prefix));
    const api={getItem:k=>raw.getItem(prefix+k),setItem:(k,v)=>raw.setItem(prefix+k,v),removeItem:k=>raw.removeItem(prefix+k),clear:()=>keys().forEach(k=>raw.removeItem(k)),key:i=>keys()[i]?.slice(prefix.length)??null};
    Object.defineProperty(api,'length',{get:()=>keys().length});
    Object.defineProperty(window,name,{value:api});
  }
  const fetch0=window.fetch;
  window.fetch=function(input,options){
    const url=new URL(input instanceof Request?input.url:input,location.href);
    if(url.origin!==location.origin)return Promise.reject(new Error('Conexões externas desativadas no teste'));
    const headers=new Headers(options?.headers||(input instanceof Request?input.headers:{}));
    headers.set('X-Nowup-Test333','1');
    return fetch0.call(this,input,{...options,headers});
  };
  const open=XMLHttpRequest.prototype.open,send=XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open=function(method,url,...args){
    if(new URL(url,location.href).origin!==location.origin)throw new Error('Conexões externas desativadas no teste');
    return open.call(this,method,url,...args);
  };
  XMLHttpRequest.prototype.send=function(...args){this.setRequestHeader('X-Nowup-Test333','1');return send.apply(this,args)};
  function stamp(form){
    if(form.action.includes('/admin/modo-teste/sair'))return;
    const url=new URL(form.action||location.href,location.href);
    if(url.origin!==location.origin)throw new Error('Formulário externo desativado no teste');
    url.searchParams.set('__nu333_test','1');form.action=url.href;
  }
  document.addEventListener('submit',event=>stamp(event.target),true);
  const submit=HTMLFormElement.prototype.submit;
  HTMLFormElement.prototype.submit=function(){stamp(this);return submit.call(this)};
})();
