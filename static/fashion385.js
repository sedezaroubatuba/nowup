(()=>{'use strict';
 if(!document.body.classList.contains('public-profile-area'))return;
 document.body.classList.add('fashion-catalog385');
 const sources=new Map([...document.querySelectorAll('[data-product]')].map(card=>[card.dataset.id,card]));
 function gallery(item){
  if(!item)return;
  const source=item.matches('[data-product]')?item:sources.get(item.dataset.source256),panel=item.matches('[data-product]')?item.querySelector('.menu-product-info'):item.querySelector('.nu201-panel');
  if(!source||!panel||panel.querySelector('.nu385-gallery'))return;
  const first=source.querySelector('img');let files=[];try{files=JSON.parse(source.dataset.fashionPhotos385||'[]');}catch(_){}
  const primary=first?.dataset.src258||first?.currentSrc||first?.src;
  const urls=[...(primary?[primary]:[]),...files.filter(file=>typeof file==='string'&&/^[a-zA-Z0-9_.-]+$/.test(file)).slice(0,4).map(file=>'/uploads/'+encodeURIComponent(file))];
  if(!urls.length)return;
  const box=document.createElement('div');box.className='nu385-gallery';
  const button=document.createElement('button');button.type='button';button.className='nu385-photo';button.setAttribute('aria-label','Ampliar foto de '+source.dataset.name);
  const photo=document.createElement('img');photo.src=urls[0];photo.alt=source.dataset.name;button.append(photo);
  button.addEventListener('click',()=>{let zoom=document.getElementById('nu385-zoom');if(!zoom){zoom=document.createElement('dialog');zoom.id='nu385-zoom';zoom.setAttribute('aria-label','Foto ampliada');const close=document.createElement('button');close.type='button';close.textContent='×';close.setAttribute('aria-label','Fechar foto');close.onclick=()=>zoom.close();zoom.append(close,document.createElement('img'));document.body.append(zoom);}zoom.querySelector('img').src=photo.src;zoom.querySelector('img').alt=photo.alt;zoom.showModal();});
  const thumbs=document.createElement('div');thumbs.className='nu385-thumbs';urls.forEach((url,index)=>{const thumb=document.createElement('button');thumb.type='button';thumb.setAttribute('aria-label','Ver foto '+(index+1));const img=document.createElement('img');img.src=url;img.alt='';img.loading='lazy';thumb.append(img);thumb.onclick=()=>{photo.src=url;};thumbs.append(thumb);});
  box.append(button,thumbs);panel.prepend(box);
 }
 document.addEventListener('click',event=>{const toggle=event.target.closest('.nu201-open'),choose=event.target.closest('.nu151-choose');if(toggle)setTimeout(()=>gallery(toggle.closest('[data-source256]')),0);if(choose)setTimeout(()=>gallery(choose.closest('[data-product]')),0);});
 // Keep the existing catalogue, banners, cart and WhatsApp checkout for this sector.
})();
