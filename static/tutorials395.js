/* Read-only guided help. Never submits a form or fills merchant data. */
(()=>{
 'use strict';
 function init(){
  const section=document.getElementById('tutoriais395'),data=window.NOWUP_TUTORIALS395;
  if(!section||!Array.isArray(data))return;
  const list=section.querySelector('[data-tutorial-list395]'),search=section.querySelector('[data-tutorial-search395]');
  const fashion=section.dataset.fashion==='1';
  const topics=data.filter(t=>fashion?!t.food&&!t.nonfashion:t.id!=='moda');
  const panel=document.createElement('aside');panel.className='nu395-guide';panel.hidden=true;
  panel.setAttribute('role','region');panel.setAttribute('aria-label','Tutorial guiado');
  const progress=document.createElement('p'),title=document.createElement('h2'),copy=document.createElement('p'),status=document.createElement('p'),actions=document.createElement('div');
  progress.className='nu395-progress';title.id='nu395-step-title';title.tabIndex=-1;panel.setAttribute('aria-labelledby',title.id);status.setAttribute('role','status');
  const button=(text,fn)=>{const b=document.createElement('button');b.type='button';b.className='btn soft';b.textContent=text;b.addEventListener('click',fn);return b;};
  let topic=null,index=0,highlight=null,described=null,opener=null,navFrame=0;
  const previous=button('Anterior',()=>show(index-1)),next=button('Próximo',()=>index+1<topic.steps.length?show(index+1):finish(true)),exit=button('Fechar tutorial',()=>finish(false));next.className='btn primary';
  actions.append(previous,next,exit);panel.append(progress,title,copy,status,actions);document.body.append(panel);copy.id='nu395-step-copy';
  function clearHighlight(){if(highlight){highlight.classList.remove('nu395-highlight');if(described===null)highlight.removeAttribute('aria-describedby');else highlight.setAttribute('aria-describedby',described);highlight=null;}if(navFrame)cancelAnimationFrame(navFrame);navFrame=0;}
  function navigate(page){const hash='#'+page;if(location.hash!==hash)history.pushState(null,'',hash);window.dispatchEvent(new Event('nowup:panelnavigate'));}
  function finish(back){clearHighlight();topic=null;panel.hidden=true;document.body.classList.remove('nu395-guiding');if(back)navigate('tutoriais395');if(opener?.isConnected&&opener.getClientRects().length)opener.focus({preventScroll:true});}
  function show(step){
   if(!topic)return;index=Math.max(0,Math.min(step,topic.steps.length-1));clearHighlight();
   const item=topic.steps[index];navigate(item.page);panel.hidden=false;document.body.classList.add('nu395-guiding');
   progress.textContent=topic.title+' · Passo '+(index+1)+' de '+topic.steps.length;title.textContent=item.title;copy.textContent=item.text;
   previous.disabled=index===0;next.textContent=index===topic.steps.length-1?'Concluir':'Próximo';status.textContent='';
   navFrame=requestAnimationFrame(()=>{navFrame=0;const target=document.querySelector(item.target);
    if(!target){status.textContent='Esta opção não está disponível nesta tela ou neste plano. Você pode continuar a leitura ou consultar o suporte.';title.focus({preventScroll:true});return;}
    for(let node=target;node;node=node.parentElement)if(node.tagName==='DETAILS')node.open=true;
    if(!target.getClientRects().length){status.textContent='Esta opção depende da configuração da loja. Confira os passos anteriores ou consulte o suporte.';title.focus({preventScroll:true});return;}
    highlight=target;described=target.getAttribute('aria-describedby');target.classList.add('nu395-highlight');target.setAttribute('aria-describedby',[described,copy.id].filter(Boolean).join(' '));
    target.scrollIntoView({block:'center',behavior:'auto'});title.focus({preventScroll:true});
   });
  }
  const normalize=s=>s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  function draw(){list.replaceChildren();const query=normalize(search.value.trim());let count=0;
   for(const t of topics){if(!normalize(t.title+' '+t.description+' '+t.steps.map(s=>s.text).join(' ')).includes(query))continue;count++;
    const card=document.createElement('article'),heading=document.createElement('h3'),description=document.createElement('p'),details=document.createElement('details'),summary=document.createElement('summary'),steps=document.createElement('ol');
    card.className='nu395-topic';heading.textContent=t.title;description.textContent=t.description;summary.textContent='Ler passo a passo';
    for(const step of t.steps){const li=document.createElement('li'),strong=document.createElement('strong'),p=document.createElement('p');strong.textContent=step.title;p.textContent=step.text;li.append(strong,p);steps.append(li);}details.append(summary,steps);
    const start=button('Mostrar no painel',()=>{opener=start;topic=t;show(0);});start.className='btn primary';
    card.append(heading,description,details,start);list.append(card);
   }
   section.querySelector('[data-tutorial-empty395]').hidden=count>0;
  }
  search.addEventListener('input',draw);
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&topic)finish(false);});
  window.addEventListener('popstate',()=>{if(topic)finish(false);});
  window.addEventListener('hashchange',()=>{if(topic&&location.hash!=='#'+topic.steps[index].page)finish(false);});
  // Existing navigation uses pushState, which does not emit hashchange.
  window.addEventListener('click',event=>{if(!topic)return;const link=event.target.closest('a[href^="#"]');if(link&&link.hash!=='#'+topic.steps[index].page)finish(false);},true);
  draw();
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
