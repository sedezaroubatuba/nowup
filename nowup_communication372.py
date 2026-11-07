"""Merchant communication: durable queues, explicit dates and future-only onboarding.

No payment inference from plan approval. Existing merchants do not receive a
retroactive welcome; no marketing consent or historical contract date is invented.
"""
import asyncio
import hashlib
import html
import json
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone, date
from urllib.parse import urlsplit
from fastapi import APIRouter, HTTPException, Request, Form
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
import nowup_admin227 as adm
import mailing

G = {}; router = APIRouter(); log = logging.getLogger(__name__)
RULES = {
 'overdue': ('Pagamento vencido · ativação opcional', 'Há um vencimento pendente no seu cadastro', 'Olá, {nome}! Existe um vencimento pendente registrado para a {loja}. Confira sua assinatura no painel. Se já pagou, entre em contato com a equipe para conferir o registro.'),
 'welcome': ('Boas-vindas', 'Bem-vindo ao NowUp!', 'Olá, {nome}! Seu cadastro da loja {loja} está confirmado. Comece pelos dados da loja, cadastre os produtos e compartilhe seu link. Estamos aqui para ajudar.'),
 'setup': ('Ajuda com a configuração · após 2 dias', 'Precisa de ajuda para montar seu cardápio?', 'Olá, {nome}! Como está a montagem do cardápio da {loja}? Comece pelo básico: nome, preço, descrição e uma foto, se desejar. Você pode completar os adicionais depois.'),
 'active': ('Acompanhamento · 3 dias após ativação', 'Como está sendo usar o NowUp?', 'Olá, {nome}! A {loja} já está ativa. Ficou alguma dúvida sobre produtos, fotos ou divulgação do link? Acesse seu painel para continuar.'),
 'contract': ('Contratação registrada', 'Sua contratação foi registrada no NowUp', 'Olá, {nome}! A contratação da {loja} foi registrada. Acesse seu painel para conferir seu cardápio. Conte conosco para começar.'),
 'trial15': ('Teste grátis · faltam 15 dias', 'Seu teste grátis termina em 15 dias', 'Olá, {nome}! O teste gratuito da {loja} termina em {fim_teste}. Confira as condições da assinatura no painel.'),
 'trial7': ('Teste grátis · faltam 7 dias', 'Seu teste grátis termina em 7 dias', 'Olá, {nome}! Seu teste gratuito termina em {fim_teste}. Aproveite para revisar seu cardápio e conferir as condições para continuar.'),
 'trial1': ('Teste grátis · falta 1 dia', 'Seu teste grátis termina amanhã', 'Olá, {nome}! O teste gratuito da {loja} termina em {fim_teste}. Acesse seu painel para conferir os próximos passos.'),
 'trial_end': ('Teste grátis encerrado', 'Seu período de teste chegou ao fim', 'Olá, {nome}! O período gratuito da {loja} terminou em {fim_teste}. Confira no painel as condições para continuar usando o NowUp.')
}
STATES = {'unknown':'Sem assinatura registrada','trial':'Teste grátis','trial_ended':'Teste encerrado','paid':'Em dia','overdue':'Inadimplente','cancelled':'Cancelada'}


def stamp(): return datetime.now(timezone.utc).isoformat()
def parse(value):
    if not value: return None
    try:
        result=datetime.fromisoformat(str(value).replace('Z','+00:00'))
        return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result.astimezone(timezone.utc)
    except (ValueError,TypeError): return None

def clean(value,maximum,required=False):
    if not isinstance(value,str) or len(value)>maximum or (required and not value.strip()): raise HTTPException(400,'Texto inválido ou muito longo.')
    return value.strip()

def link(value):
    value=clean(value,1000)
    if value and (urlsplit(value).scheme!='https' or not urlsplit(value).netloc or urlsplit(value).username): raise HTTPException(400,'Informe um link HTTPS válido para o tutorial.')
    return value

def settings(c):
    return json.loads(c.execute('SELECT data FROM communication372_settings WHERE id=1').fetchone()[0])

def initialize():
    with adm.connection() as c:
        schema(c)
        # Establish an honest baseline for pre-existing stores. No retroactive activation date.
        baseline(c)
        c.commit()

def schema(c):
        c.executescript('''
CREATE TABLE IF NOT EXISTS communication372_settings(id INTEGER PRIMARY KEY,data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS communication372_contacts(
 professional_id INTEGER PRIMARY KEY REFERENCES professionals(id) ON DELETE CASCADE,
 welcome_eligible INTEGER NOT NULL DEFAULT 0, campaign TEXT NOT NULL DEFAULT '',
 activated_at TEXT NOT NULL DEFAULT '', contracted_at TEXT NOT NULL DEFAULT '',
 trial_start TEXT NOT NULL DEFAULT '', trial_end TEXT NOT NULL DEFAULT '',
 accepted_at TEXT NOT NULL DEFAULT '', terms_version TEXT NOT NULL DEFAULT '',
 contracted_cents INTEGER, contract_reference TEXT NOT NULL DEFAULT '',
 marketing_allowed INTEGER NOT NULL DEFAULT 0, marketing_email_hash TEXT NOT NULL DEFAULT '',
 marketing_updated_at TEXT NOT NULL DEFAULT '', optout_token TEXT NOT NULL DEFAULT '',
 observed_active INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS communication372_campaigns(
 id INTEGER PRIMARY KEY AUTOINCREMENT, request_key TEXT NOT NULL UNIQUE,
 subject TEXT NOT NULL, body TEXT NOT NULL, tutorial TEXT NOT NULL DEFAULT '',
 purpose TEXT NOT NULL, channels TEXT NOT NULL, scheduled_at TEXT NOT NULL,
 audience TEXT NOT NULL, created_by TEXT NOT NULL, created_at TEXT NOT NULL,
 cancelled INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS communication372_deliveries(
 id INTEGER PRIMARY KEY AUTOINCREMENT, unique_key TEXT NOT NULL UNIQUE,
 campaign_id INTEGER REFERENCES communication372_campaigns(id),
 professional_id INTEGER NOT NULL REFERENCES professionals(id) ON DELETE CASCADE,
 channel TEXT NOT NULL, purpose TEXT NOT NULL, rule_key TEXT NOT NULL DEFAULT '',
 subject TEXT NOT NULL, body TEXT NOT NULL, tutorial TEXT NOT NULL DEFAULT '',
 recipient TEXT NOT NULL DEFAULT '', scheduled_at TEXT NOT NULL,
 state TEXT NOT NULL DEFAULT 'pending', error TEXT NOT NULL DEFAULT '',
 created_at TEXT NOT NULL, sent_at TEXT NOT NULL DEFAULT '', claimed_at TEXT NOT NULL DEFAULT '');
CREATE INDEX IF NOT EXISTS communication372_queue ON communication372_deliveries(state,scheduled_at,id);
CREATE INDEX IF NOT EXISTS communication373_panel_lookup ON communication372_deliveries(professional_id,channel,state,sent_at);
''')
        defaults={'tutorial':'','onboarding':True,'rules':{key:{'enabled':key!='overdue','subject':value[1],'body':value[2],'channels':['email','panel']} for key,value in RULES.items()}}
        c.execute('INSERT OR IGNORE INTO communication372_settings(id,data) VALUES(1,?)',(json.dumps(defaults,ensure_ascii=False),))
        cfg=settings(c)
        if any(key not in cfg['rules'] for key in RULES):
            for key in RULES:cfg['rules'].setdefault(key,defaults['rules'][key])
            c.execute('UPDATE communication372_settings SET data=? WHERE id=1',(json.dumps(cfg,ensure_ascii=False),))

def baseline(c):
        for p in c.execute('SELECT id,blocked,admission_status,plan_active FROM professionals WHERE is_demo=0'):
            active=int(not p['blocked'] and p['admission_status']=='approved' and p['plan_active'] not in ('none',''))
            c.execute('INSERT OR IGNORE INTO communication372_contacts(professional_id,observed_active,created_at,optout_token) VALUES(?,?,?,?)',(p['id'],active,stamp(),secrets.token_urlsafe(32)))
        c.commit()


def signup(c,pid,accepted_at,marketing=False):
    """Called in the registration transaction; welcome waits for verified e-mail."""
    email=c.execute('SELECT u.email FROM users u JOIN professionals p ON p.user_id=u.id WHERE p.id=?',(pid,)).fetchone()[0]
    c.execute('INSERT INTO communication372_contacts(professional_id,welcome_eligible,accepted_at,terms_version,marketing_allowed,marketing_email_hash,marketing_updated_at,optout_token,created_at) VALUES(?,1,?,?,?,?,?,?,?)',(pid,accepted_at,'termos-cadastro-2026-11-v372',int(marketing),digest(email),accepted_at,secrets.token_urlsafe(32),accepted_at))


def digest(value):return hashlib.sha256(value.strip().lower().encode()).hexdigest()

def contacts(c):
    metas=adm.metadata(c,'storemeta');today=datetime.now(adm.TZ).date().isoformat(); result=[]
    for raw in c.execute('''SELECT p.*,u.email,u.name owner,u.email_verified,u.is_active,
 t.welcome_eligible,t.campaign,t.activated_at,t.contracted_at,t.trial_start,t.trial_end,
 t.accepted_at,t.terms_version,t.contracted_cents,t.contract_reference,t.marketing_allowed,
 t.marketing_email_hash,t.marketing_updated_at,t.optout_token,t.observed_active,
 COALESCE(pr.total,0) product_count,COALESCE(o.total,0) order_count
 FROM professionals p JOIN users u ON u.id=p.user_id
 JOIN communication372_contacts t ON t.professional_id=p.id
 LEFT JOIN (SELECT professional_id,COUNT(*) total FROM products GROUP BY professional_id) pr ON pr.professional_id=p.id
 LEFT JOIN (SELECT professional_id,COUNT(*) total FROM orders GROUP BY professional_id) o ON o.professional_id=p.id
 WHERE p.is_demo=0 ORDER BY p.id DESC'''):
        p=dict(raw);meta=metas.get(p['id'],{})
        trial_end=p['trial_end'] or meta.get('trialUntil',''); due=p['billing_due_date'] or '';cancelled=meta.get('cancelledAt','')
        if cancelled: state='cancelled'
        elif trial_end and not p['billing_last_paid']:state='trial' if trial_end[:10]>=today else 'trial_ended'
        elif due and due[:10]<today:state='overdue'
        elif p['billing_last_paid']:state='paid'
        else:state='unknown'
        active=bool(p['is_active'] and not p['blocked'] and p['admission_status']=='approved' and p['plan_active'] not in ('none',''))
        stage='published' if active and p['product_count'] else ('configuring' if p['product_count'] else 'incomplete')
        result.append({'id':p['id'],'userId':p['user_id'],'name':p['display_name'],'owner':p['owner'],'email':p['email'],'phone':p['whatsapp'],'city':p['city'],'state':p['state'],
          'plan':p['plan_active'] if p['plan_active'] not in ('none','') else p['plan_requested'],'stage':stage,'subscription':state,'active':active,'verified':bool(p['email_verified']),'enabled':bool(p['is_active']),
          'createdAt':p['created_at'],'activatedAt':p['activated_at'],'contractedAt':p['contracted_at'],'trialStart':p['trial_start'],'trialEnd':trial_end,'due':due,'lastPaid':p['billing_last_paid'],
          'campaign':p['campaign'],'acceptedAt':p['accepted_at'],'termsVersion':p['terms_version'],'contractedCents':p['contracted_cents'],'contractReference':p['contract_reference'],'products':p['product_count'],'orders':p['order_count'],
          'marketing':bool(p['marketing_allowed'] and p['marketing_email_hash']==digest(p['email'])),'marketingUpdatedAt':p['marketing_updated_at'],
          '_welcome':p['welcome_eligible'],'_observed':p['observed_active'],'_token':p['optout_token']})
    return result


def public_contact(p):return {k:v for k,v in p.items() if not k.startswith('_')}
def eligible(p,purpose,channel):return p['enabled'] and (channel!='email' or p['verified']) and (purpose!='promotion' or p['marketing'])
def render_text(text,p):
    values={'nome':p['owner'],'loja':p['name'],'fim_teste':('/'.join(reversed(p['trialEnd'][:10].split('-'))) if p['trialEnd'] else 'não informado')}
    for key,value in values.items():text=text.replace('{'+key+'}',value)
    return text

def email_html(subject,body,tutorial,p):
    esc=html.escape;base=os.getenv('NOWUP_BASE_URL','').rstrip('/')
    content='<div style="font:16px Arial,sans-serif;max-width:580px;margin:auto;color:#243047"><h2 style="color:#7023bc">'+esc(subject)+'</h2><p>'+esc(body).replace('\n','<br>')+'</p>'
    if tutorial:content+='<p><a href="'+esc(tutorial,quote=True)+'">Assistir tutorial</a></p>'
    if base:content+='<p><a href="'+esc(base,quote=True)+'/painel">Acessar meu painel</a></p><p><a href="'+esc(base,quote=True)+'/comunicacoes372/preferencias?token='+p['_token']+'">Preferências de comunicação</a></p>'
    return content+'</div>'


def enqueue(c,p,key,subject,body,tutorial,channels,scheduled,purpose='service',campaign=None,rule=''):
    for channel in channels:
        if not eligible(p,purpose,channel):continue
        c.execute('''INSERT OR IGNORE INTO communication372_deliveries(unique_key,campaign_id,professional_id,channel,purpose,rule_key,subject,body,tutorial,recipient,scheduled_at,created_at)
 VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',(key+':'+channel,campaign,p['id'],channel,purpose,rule,render_text(subject,p),render_text(body,p),tutorial,p['email'],scheduled,stamp()))


def generate(c,now=None):
    now=now or datetime.now(timezone.utc);cfg=settings(c);local=now.astimezone(adm.TZ).date()
    for p in contacts(c):
        if p['active'] and not p['_observed']:
            c.execute("UPDATE communication372_contacts SET observed_active=1,activated_at=CASE WHEN activated_at='' THEN ? ELSE activated_at END WHERE professional_id=?",(now.isoformat(),p['id']))
            p['activatedAt']=p['activatedAt'] or now.isoformat()
        if not p['enabled'] or not p['verified']:continue
        triggers={}
        if p['_welcome']:triggers['welcome']='signup';start=parse(p['createdAt']);triggers.update({'setup':'signup'} if start and now>=start+timedelta(days=2) and p['stage']!='published' else {})
        activation=parse(p['activatedAt'])
        if activation and p['active'] and now>=activation+timedelta(days=3):triggers['active']=p['activatedAt']
        if p['contractedAt'] and p['contractedAt'][:10]<=local.isoformat():triggers['contract']=p['contractedAt']
        if p['subscription'] in ('trial','trial_ended') and p['trialEnd']:
            end=parse(p['trialEnd'])
            if end:
                days=(date.fromisoformat(p['trialEnd'][:10])-local).days
                if days in (15,7,1):triggers['trial'+str(days)]=p['trialEnd']
                elif days<0:triggers['trial_end']=p['trialEnd']
        if p['subscription']=='overdue' and p['due']:triggers['overdue']=p['due']
        for key,period in triggers.items():
            rule=cfg['rules'][key]
            if rule['enabled'] and (cfg['onboarding'] or key not in ('welcome','setup','active')):
                enqueue(c,p,'auto:'+key+':'+str(p['id'])+':'+period,rule['subject'],rule['body'],cfg['tutorial'],rule['channels'],now.isoformat(),rule=key)
    c.commit()


def deliver_one(c,d,now):
    p=next((p for p in contacts(c) if p['id']==d['professional_id']),None)
    reason=''
    if not p or not eligible(p,d['purpose'],d['channel']):reason='Contato indisponível ou sem autorização atual.'
    elif d['channel']=='email' and p['email']!=d['recipient']:reason='E-mail mudou depois do agendamento.'
    elif d['campaign_id'] and c.execute('SELECT cancelled FROM communication372_campaigns WHERE id=?',(d['campaign_id'],)).fetchone()[0]:reason='Campanha cancelada.'
    elif d['rule_key']:
        cfg=settings(c)
        if not cfg['rules'][d['rule_key']]['enabled']:reason='Automação desativada.'
        if not cfg['onboarding'] and d['rule_key'] in ('welcome','setup','active'):reason='Acompanhamento automático pausado.'
        if d['rule_key'] in ('trial15','trial7','trial1') and p['trialEnd']:
            days=(date.fromisoformat(p['trialEnd'][:10])-now.astimezone(adm.TZ).date()).days
            if days!=int(d['rule_key'][5:]):reason='Prazo deste lembrete já passou.'
        if d['rule_key']=='active' and not p['active']:reason='Loja não está mais ativa.'
        if d['rule_key']=='contract' and (not p['contractedAt'] or p['subscription']=='cancelled'):reason='Contratação alterada ou cancelada.'
        if d['rule_key'].startswith('trial') and (p['subscription'] not in ('trial','trial_ended') or p['trialEnd'] not in d['unique_key']):reason='Período gratuito alterado ou assinatura já paga.'
        if d['rule_key']=='overdue' and (p['subscription']!='overdue' or p['due'] not in d['unique_key']):reason='Pagamento registrado ou vencimento alterado.'
        if d['rule_key']=='setup' and p['stage']=='published':reason='Cardápio já publicado.'
    if reason:
        c.execute("UPDATE communication372_deliveries SET state='skipped',error=? WHERE id=? AND state='pending'",(reason,d['id']));c.commit();return
    if d['channel']=='email' and not mailing.configured():return
    claimed=c.execute("UPDATE communication372_deliveries SET state='sending',claimed_at=? WHERE id=? AND state='pending'",(now.isoformat(),d['id'])).rowcount
    if not claimed:c.rollback();return
    if d['channel']=='panel':
        c.execute('INSERT INTO notifications(user_id,title,message,link,created_at) VALUES(?,?,?,?,?)',(p['userId'],d['subject'],d['body'],d['tutorial'] or '/painel',now.isoformat()))
        c.execute("UPDATE communication372_deliveries SET state='sent',sent_at=? WHERE id=?",(now.isoformat(),d['id']));c.commit();return
    c.commit() # Persist the claim before the external effect. Never retry an uncertain result automatically.
    try:
        ok=G['send_email'](p['email'],p['owner'],d['subject'],email_html(d['subject'],d['body'],d['tutorial'],p))
        state='sent' if ok else 'uncertain';error='' if ok else 'Envio não confirmado pelo provedor. Confira antes de tentar novamente.'
    except Exception:state='uncertain';error='Envio não confirmado. Verifique o provedor antes de reenviar.'
    c.execute('UPDATE communication372_deliveries SET state=?,error=?,sent_at=? WHERE id=?',(state,error,now.isoformat() if state=='sent' else '',d['id']));c.commit()


def tick(should_stop=lambda:False):
    with adm.connection() as c:
        c.execute("UPDATE communication372_deliveries SET state='uncertain',error='Processamento interrompido; confira o provedor antes de reenviar.' WHERE state='sending' AND claimed_at<?",((datetime.now(timezone.utc)-timedelta(minutes=10)).isoformat(),));c.commit()
        baseline(c)
        generate(c)
        # Panel notices continue even while the e-mail service is unavailable.
        for row in c.execute("SELECT * FROM communication372_deliveries WHERE state='pending' AND scheduled_at<=? ORDER BY channel DESC,id LIMIT 10",(stamp(),)).fetchall():
            if should_stop():break
            deliver_one(c,dict(row),datetime.now(timezone.utc))


def admin(request,c,mutation=False):
    if mutation:adm.csrf(request)
    actor=adm.auth(request,c)
    if not actor['super']:raise HTTPException(403,'Comunicação e dados de assinatura restritos ao Super ADM.')
    return actor


def response(c):
    cfg=settings(c)
    campaigns=[dict(r) for r in c.execute('SELECT * FROM communication372_campaigns ORDER BY id DESC LIMIT 100')]
    deliveries=[dict(r) for r in c.execute('''SELECT d.*,p.display_name store FROM communication372_deliveries d JOIN professionals p ON p.id=d.professional_id ORDER BY d.id DESC LIMIT 500''')]
    counts={r['state']:r['total'] for r in c.execute('SELECT state,COUNT(*) total FROM communication372_deliveries GROUP BY state')}
    return JSONResponse({'contacts':[public_contact(p) for p in contacts(c)],'settings':cfg,'rules':{k:v[0] for k,v in RULES.items()},'campaigns':campaigns,'deliveries':deliveries,'counts':counts,'emailReady':mailing.configured(),'billingConnected':False},headers={'Cache-Control':'private, no-store'})

@router.get('/admin/super/api/communication')
def get_state(request:Request):
    with adm.connection() as c:admin(request,c);return response(c)

@router.post('/admin/super/api/communication/settings')
async def update_settings(request:Request):
    body=await request.json()
    with adm.connection() as c:
        a=admin(request,c,True);cfg=settings(c)
        cfg['tutorial']=link(body.get('tutorial',''))
        if type(body.get('onboarding')) is not bool:raise HTTPException(400,'Configuração inválida.')
        cfg['onboarding']=body['onboarding']
        for key in RULES:
            rule=body.get('rules',{}).get(key,{})
            if type(rule.get('enabled')) is not bool:raise HTTPException(400,'Configuração de automação inválida.')
            channels=rule.get('channels',[])
            if not isinstance(channels,list) or not channels or len(channels)!=len(set(channels)) or any(v not in ('email','panel') for v in channels):raise HTTPException(400,'Escolha um canal válido.')
            cfg['rules'][key]={'enabled':rule['enabled'],'subject':clean(rule.get('subject'),160,True),'body':clean(rule.get('body'),6000,True),'channels':channels}
        c.execute('UPDATE communication372_settings SET data=? WHERE id=1',(json.dumps(cfg,ensure_ascii=False),));adm.audit(c,a,'Configurações de comunicação atualizadas');c.commit();return response(c)

@router.post('/admin/super/api/communication/group')
async def update_group(request:Request):
    body=await request.json()
    with adm.connection() as c:
        a=admin(request,c,True);ids=body.get('ids')
        if not isinstance(ids,list) or not ids or len(ids)>5000 or any(type(v) is not int for v in ids):raise HTTPException(400,'Selecione os lojistas.')
        campaign=clean(body.get('campaign'),180,True)
        start=clean(body.get('trialStart',''),10);end=clean(body.get('trialEnd',''),10)
        if bool(start)!=bool(end) or (start and (not parse(start) or not parse(end) or len(start)!=10 or len(end)!=10 or start>end)):raise HTTPException(400,'Confira início e fim do teste.')
        known={p['id'] for p in contacts(c)}
        if set(ids)-known:raise HTTPException(400,'A seleção mudou. Atualize a lista de lojistas.')
        for pid in set(ids):
            if start:c.execute('UPDATE communication372_contacts SET campaign=?,trial_start=?,trial_end=? WHERE professional_id=?',(campaign,start,end,pid))
            else:c.execute('UPDATE communication372_contacts SET campaign=? WHERE professional_id=?',(campaign,pid))
        adm.audit(c,a,'Grupo de comunicação atualizado: '+str(len(set(ids)))+' lojistas');c.commit();return response(c)

@router.post('/admin/super/api/communication/contact/{pid}')
async def update_contact(request:Request,pid:int):
    body=await request.json()
    with adm.connection() as c:
        a=admin(request,c,True)
        if not c.execute('SELECT 1 FROM communication372_contacts WHERE professional_id=?',(pid,)).fetchone():raise HTTPException(404,'Loja não encontrada.')
        fields={}
        for key in ('campaign','contract_reference'):fields[key]=clean(body.get(key,''),180)
        for key in ('trial_start','trial_end','contracted_at'):
            value=clean(body.get(key,''),40)
            if value and (not parse(value) or len(value)!=10):raise HTTPException(400,'Informe uma data válida.')
            fields[key]=value
        if bool(fields['trial_start'])!=bool(fields['trial_end']) or fields['trial_start']>fields['trial_end']:raise HTTPException(400,'Informe início e fim do teste na ordem correta.')
        cents=body.get('contracted_cents')
        if cents is not None and (type(cents) is not int or not 0<=cents<=10000000):raise HTTPException(400,'Valor contratado inválido.')
        c.execute('UPDATE communication372_contacts SET campaign=?,contract_reference=?,trial_start=?,trial_end=?,contracted_at=?,contracted_cents=? WHERE professional_id=?',(*fields.values(),cents,pid))
        adm.audit(c,a,'Datas de teste/contratação registradas sem alterar cobrança ou acesso',pid);c.commit();return response(c)


def compose(body,c):
    subject=clean(body.get('subject'),160,True);text=clean(body.get('body'),6000,True);tutorial=link(body.get('tutorial',''))
    purpose=body.get('purpose');channels=body.get('channels');ids=body.get('ids')
    if purpose not in ('service','promotion'):raise HTTPException(400,'Escolha a finalidade da mensagem.')
    if not isinstance(channels,list) or not channels or len(channels)!=len(set(channels)) or any(v not in ('email','panel') for v in channels):raise HTTPException(400,'Canal inválido.')
    if not isinstance(ids,list) or not ids or len(ids)>5000 or any(type(v) is not int for v in ids):raise HTTPException(400,'Selecione de 1 a 5.000 lojas.')
    selected=set(ids);people=[p for p in contacts(c) if p['id'] in selected]
    targets=[(p,ch) for p in people for ch in channels if eligible(p,purpose,ch)]
    scheduled=parse(body.get('scheduledAt') or stamp())
    if not scheduled:raise HTTPException(400,'Data de envio inválida.')
    return subject,text,tutorial,purpose,channels,people,targets,scheduled.isoformat()

@router.post('/admin/super/api/communication/preview')
async def preview(request:Request):
    body=await request.json()
    with adm.connection() as c:
        admin(request,c,True);subject,text,tutorial,purpose,channels,people,targets,scheduled=compose(body,c)
        return {'recipients':len({p['id'] for p,ch in targets}),'deliveries':len(targets),'excluded':len(set(body['ids']))-len({p['id'] for p,ch in targets}),'subject':render_text(subject,people[0]) if people else subject,'body':render_text(text,people[0]) if people else text,'tutorial':tutorial,'scheduledAt':scheduled}

@router.post('/admin/super/api/communication/send')
async def send(request:Request):
    body=await request.json()
    with adm.connection() as c:
        a=admin(request,c,True)
        c.execute('BEGIN IMMEDIATE')
        request_key=clean(body.get('requestKey'),100,True)
        if c.execute('SELECT id FROM communication372_campaigns WHERE request_key=?',(request_key,)).fetchone():return response(c)
        subject,text,tutorial,purpose,channels,people,targets,scheduled=compose(body,c)
        if not targets:raise HTTPException(400,'Nenhum destinatário elegível. Confira a verificação do e-mail e as autorizações.')
        if 'email' in channels and not mailing.configured():raise HTTPException(409,'O envio de e-mail não está configurado no servidor.')
        pid=c.execute('INSERT INTO communication372_campaigns(request_key,subject,body,tutorial,purpose,channels,scheduled_at,audience,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)',(request_key,subject,text,tutorial,purpose,json.dumps(channels),scheduled,json.dumps(sorted({p['id'] for p,ch in targets})),a['actor_id'],stamp())).lastrowid
        for p in people:enqueue(c,p,'campaign:'+str(pid)+':'+str(p['id']),subject,text,tutorial,channels,scheduled,purpose,pid)
        adm.audit(c,a,'Campanha de comunicação agendada: '+str(len({p['id'] for p,ch in targets}))+' lojistas',pid);c.commit();return response(c)

@router.post('/admin/super/api/communication/cancel/{cid}')
def cancel(request:Request,cid:int):
    with adm.connection() as c:
        a=admin(request,c,True)
        c.execute('UPDATE communication372_campaigns SET cancelled=1 WHERE id=?',(cid,))
        c.execute("UPDATE communication372_deliveries SET state='cancelled' WHERE campaign_id=? AND state='pending'",(cid,));adm.audit(c,a,'Campanha cancelada; mensagens já enviadas não são desfeitas',cid);c.commit();return response(c)

@router.get('/comunicacoes372/preferencias',response_class=HTMLResponse)
def preference_page(token:str=''):
    with adm.connection() as c:
        row=c.execute('SELECT marketing_allowed FROM communication372_contacts WHERE optout_token=?',(token,)).fetchone()
        if not row or not token:raise HTTPException(404,'Link inválido.')
    return HTMLResponse('<!doctype html><html lang="pt-BR"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Comunicações NowUp</title><main style="font:18px system-ui;max-width:500px;margin:50px auto;padding:24px"><h1>Preferências de comunicação</h1><p>Você pode deixar de receber novidades e promoções. Avisos sobre sua conta e assinatura continuam disponíveis.</p><form method="post"><input type="hidden" name="token" value="'+html.escape(token,quote=True)+'"><button style="padding:16px;background:#7023bc;color:white;border:0;border-radius:8px">Não receber promoções</button></form></main></html>',headers={'Cache-Control':'no-store','Referrer-Policy':'no-referrer'})

@router.post('/comunicacoes372/preferencias',response_class=HTMLResponse)
def preference_save(token:str=Form(...)):
    with adm.connection() as c:
        if not token or not c.execute('SELECT 1 FROM communication372_contacts WHERE optout_token=?',(token,)).fetchone():raise HTTPException(404)
        c.execute('UPDATE communication372_contacts SET marketing_allowed=0,marketing_updated_at=? WHERE optout_token=?',(stamp(),token));c.commit()
    return HTMLResponse('<h1>Preferência salva</h1><p>Você não receberá mais novidades e promoções por esta lista.</p>',headers={'Cache-Control':'no-store'})


# Popup notices only include communication deliveries, never order/chat alerts.
CARD_MATCH373 = """EXISTS (SELECT 1 FROM communication372_deliveries d
 JOIN professionals p ON p.id=d.professional_id
 WHERE p.user_id=n.user_id AND d.channel='panel' AND d.state='sent'
 AND d.sent_at=n.created_at AND d.subject=n.title AND d.body=n.message)"""

@router.get('/painel/comunicacao/cards')
def merchant_cards373(request:Request):
    u=G['require_user'](request,'professional')
    with adm.connection() as c:
        notices=c.execute("SELECT n.id,n.title,n.message,n.link,n.created_at FROM notifications n WHERE n.user_id=? AND COALESCE(n.read_at,'')='' AND "+CARD_MATCH373+" ORDER BY n.id LIMIT 50",(u['id'],)).fetchall()
        return JSONResponse({'notices':[dict(n) for n in notices]},headers={'Cache-Control':'private, no-store','Vary':'Cookie'})

@router.post('/painel/comunicacao/cards/{notice_id}/fechar')
def dismiss_card373(request:Request,notice_id:int):
    u=G['require_user'](request,'professional')
    from nowup_runtime238 import mutation_origin_allowed
    if request.headers.get('x-nowup-notice')!='373' or not mutation_origin_allowed(request):raise HTTPException(403,'Atualize o painel para fechar a mensagem.')
    with adm.connection() as c:
        row=c.execute('SELECT n.id FROM notifications n WHERE n.id=? AND n.user_id=? AND '+CARD_MATCH373,(notice_id,u['id'])).fetchone()
        if not row:raise HTTPException(404,'Mensagem não encontrada.')
        c.execute("UPDATE notifications SET read_at=? WHERE id=? AND user_id=? AND COALESCE(read_at,'')=''",(stamp(),notice_id,u['id']));c.commit()
        return JSONResponse({'closed':True},headers={'Cache-Control':'no-store'})

def install(g):
    G.update(g);app=g['app'];app.include_router(router);app.router.add_event_handler('startup',initialize)
    task=None;stop=None
    async def runner():
        while not stop.is_set():
            try:await asyncio.to_thread(tick,stop.is_set)
            except Exception:log.exception('Communication queue processing failed')
            try:await asyncio.wait_for(stop.wait(),timeout=60)
            except asyncio.TimeoutError:pass
    async def start():
        nonlocal task,stop
        if os.getenv('NOWUP_COMMUNICATION_WORKER','1')=='0':return
        stop=asyncio.Event();task=asyncio.create_task(runner())
    async def shutdown():
        if task:
            stop.set();await task
    app.router.add_event_handler('startup',start)
    # Stop before closing the database pool (registered earlier).
    app.router.on_shutdown.insert(0,shutdown)
