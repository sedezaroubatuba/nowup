/* Decoration only: no changes to authentication, cart or order handling. */
(() => {
 'use strict';
 const horizontal='/static/nowup-logo185.png?v=196';
 const stacked='/static/nowup-logo-stacked185.png?v=196';
 document.querySelectorAll('img.nowup-official-logo').forEach(img => {
   const picture=document.createElement('picture');
   const source=document.createElement('source');
   source.media='(max-width:350px)';source.srcset=stacked;
   img.before(picture);picture.append(source,img);img.src=horizontal;
 });
 document.querySelectorAll('img.nowup-official-icon').forEach(img=>{img.src='/static/nowup-icon100.png?v=196';});
 const card=document.querySelector('body.nowup-login-white .formCard');
 if(card && !card.querySelector('.nowup-login-brand185')) {
   const img=document.createElement('img');img.className='nowup-login-brand185';
   img.src=horizontal;img.alt='NowUp Brasil';img.width=340;img.height=136;card.prepend(img);
 }
})();
