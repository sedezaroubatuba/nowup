function acceptCookies(){localStorage.setItem('nowup_cookies','1');const e=document.getElementById('cookie');if(e)e.remove()}
document.addEventListener('DOMContentLoaded',()=>{
  document.querySelectorAll('form[action*="/excluir"], form[data-confirm-delete]').forEach(form=>form.addEventListener('submit',event=>{
    if(!window.confirm('Você realmente deseja excluir? Essa ação não poderá ser desfeita.'))event.preventDefault();
  }));
  document.querySelectorAll('[data-hero-editor]').forEach(editor=>{
    const input=editor.querySelector('input[type="file"]'),preview=editor.querySelector('.hero-live-preview'),img=preview?.querySelector('img');
    const val=name=>editor.querySelector(`[name="${name}"]`)?.value;
    const sync=()=>{if(!preview||!img)return;img.style.filter=`brightness(${val('brightness')||100}%)`;img.style.transform=`scale(${(Number(val('zoom'))||100)/100})`;img.style.objectPosition=`${val('position_x')||50}% ${val('position_y')||50}%`;preview.style.height=`${preview.classList.contains('mobile-preview')?(val('mobile_height')||540):(val('desktop_height')||540)}px`;editor.querySelectorAll('[data-value-for]').forEach(out=>out.textContent=val(out.dataset.valueFor));};
    input?.addEventListener('change',()=>{const file=input.files?.[0];if(file&&img){img.src=URL.createObjectURL(file);preview.classList.add('has-image');sync()}});
    editor.querySelectorAll('input[type="range"],select').forEach(field=>field.addEventListener('input',sync));
    editor.querySelectorAll('[data-preview-mode]').forEach(button=>button.addEventListener('click',()=>{preview.classList.toggle('mobile-preview',button.dataset.previewMode==='mobile');editor.querySelectorAll('[data-preview-mode]').forEach(b=>b.classList.toggle('active',b===button));sync()}));sync();
  });
  document.querySelectorAll('form[action*="/editar"]').forEach(form=>{
    const fields=[...form.querySelectorAll('input,select,textarea')];
    const save=form.querySelector('button[type="submit"],button:not([type])');
    if(!fields.length||!save)return;
    fields.forEach(field=>field.disabled=true);save.hidden=true;
    const edit=document.createElement('button');edit.type='button';edit.className='btn soft';edit.textContent='Editar';
    edit.addEventListener('click',()=>{fields.forEach(field=>field.disabled=false);save.hidden=false;edit.hidden=true;const first=fields.find(field=>field.type!=='hidden');if(first)first.focus()});
    form.prepend(edit);
  });
  document.querySelectorAll('[data-banner-editor]').forEach(editor=>{
    const input=editor.querySelector('input[type="file"]'),preview=editor.querySelector('.banner-live-preview'),img=preview?.querySelector('img');
    const sync=()=>{
      if(!preview||!img)return;
      const val=name=>editor.querySelector(`[name="${name}"]`)?.value;
      img.style.filter=`brightness(${val('brightness')||100}%)`;
      img.style.transform=`scale(${(Number(val('zoom'))||100)/100})`;
      img.style.objectPosition=`${val('position_x')||50}% ${val('position_y')||50}%`;
      preview.style.height=`${preview.classList.contains('mobile-preview')?(val('mobile_height')||240):(val('desktop_height')||360)}px`;
      editor.querySelectorAll('[data-value-for]').forEach(out=>out.textContent=val(out.dataset.valueFor));
    };
    input?.addEventListener('change',()=>{const file=input.files?.[0];if(file&&img){img.src=URL.createObjectURL(file);preview.classList.add('has-image');sync()}});
    editor.querySelectorAll('input[type="range"],select').forEach(field=>field.addEventListener('input',sync));
    editor.querySelectorAll('[data-preview-mode]').forEach(button=>button.addEventListener('click',()=>{preview.classList.toggle('mobile-preview',button.dataset.previewMode==='mobile');editor.querySelectorAll('[data-preview-mode]').forEach(b=>b.classList.toggle('active',b===button));sync()}));
    sync();
  });
  if(localStorage.getItem('nowup_cookies')){const e=document.getElementById('cookie');if(e)e.remove()}
  const slider=document.querySelector('[data-slider]');
  if(!slider)return;
  const slides=[...slider.querySelectorAll('.ad-slide')],dots=[...slider.querySelectorAll('[data-slide]')],prev=slider.querySelector('[data-prev]'),next=slider.querySelector('[data-next]');
  let current=0,timer;
  const show=i=>{current=(i+slides.length)%slides.length;slides.forEach((s,n)=>s.classList.toggle('active',n===current));dots.forEach((d,n)=>d.classList.toggle('active',n===current));const active=slides[current];if(active){slider.style.setProperty('--desktop-height',active.style.getPropertyValue('--desktop-height')||'360px');slider.style.setProperty('--mobile-height',active.style.getPropertyValue('--mobile-height')||'240px')}};
  const start=()=>{clearInterval(timer);if(slides.length>1)timer=setInterval(()=>show(current+1),Number(slider.dataset.interval)||5000)};
  dots.forEach((d,i)=>d.addEventListener('click',()=>{show(i);start()}));
  if(prev)prev.addEventListener('click',()=>{show(current-1);start()});
  if(next)next.addEventListener('click',()=>{show(current+1);start()});
  let touchX=0;
  slider.addEventListener('touchstart',e=>{touchX=e.changedTouches[0].screenX;clearInterval(timer)},{passive:true});
  slider.addEventListener('touchend',e=>{const distance=e.changedTouches[0].screenX-touchX;if(Math.abs(distance)>45)show(current+(distance<0?1:-1));start()},{passive:true});
  slider.addEventListener('mouseenter',()=>clearInterval(timer));slider.addEventListener('mouseleave',start);show(0);start();
})
