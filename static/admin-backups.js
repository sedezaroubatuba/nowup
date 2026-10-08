(() => {
 const panel=document.querySelector('[data-backup-panel]'); if(!panel)return;
 const status=panel.querySelector('[data-backup-status]');const send=panel.querySelector('[data-backup-send]');
 const date=value=>value?new Date(value).toLocaleString('pt-BR'):'Nenhum envio confirmado';
 async function refresh(){try{const response=await fetch('/admin/backups/status',{credentials:'same-origin',cache:'no-store'});if(!response.ok)throw Error();const data=await response.json();status.textContent=(data.running?'Backup em andamento. ': '')+'Armazenamento: '+(data.configured?'configurado':'ainda não configurado')+'. Automático: '+(data.automatic?'ativado':'desativado')+'. Última cópia externa: '+date(data.last_external)+(data.error?' — '+data.error:'')+(data.warning?' — '+data.warning:'');send.disabled=!data.configured||data.running;}catch(error){status.textContent='Não foi possível consultar o backup. Confira se sua sessão de ADM continua ativa.';send.disabled=true;}}
 send.addEventListener('click',async()=>{send.disabled=true;status.textContent='Solicitando envio…';try{const response=await fetch('/admin/backups/enviar',{method:'POST',credentials:'same-origin'});const result=await response.json();if(!response.ok)throw Error(result.detail||'Falha ao solicitar backup.');status.textContent=result.message;}catch(error){status.textContent=error.message;send.disabled=false;}});
 panel.querySelector('[data-backup-refresh]').addEventListener('click',refresh);
 refresh();setInterval(()=>{if(!document.hidden)refresh();},10000);
})();
