function acceptCookies(){localStorage.setItem('nowup_cookies','1');const e=document.getElementById('cookie');if(e)e.remove()}
document.addEventListener('DOMContentLoaded',()=>{if(localStorage.getItem('nowup_cookies')){const e=document.getElementById('cookie');if(e)e.remove()}})
