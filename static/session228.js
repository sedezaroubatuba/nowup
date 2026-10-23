(()=>{
 const clear=()=>{try{localStorage.removeItem('nowup_session');sessionStorage.clear()}catch(_){}};
 if(new URLSearchParams(location.search).get('logout')==='ok')clear();
 document.addEventListener('submit',event=>{const form=event.target;if(!(form instanceof HTMLFormElement))return;const path=new URL(form.action,location.href).pathname;if(!['/logout','/sair'].includes(path))return;event.preventDefault();if(form.dataset.busy228)return;form.dataset.busy228='1';fetch(form.action,{method:'POST',body:new FormData(form),credentials:'same-origin'}).then(r=>{if(!r.ok)throw Error('Não foi possível sair. Tente novamente.');clear();location.assign('/entrar?logout=ok')}).catch(e=>{form.dataset.busy228='';alert(e.message)})});
})();
