"""Server-only Asaas integration. Durable outbox, idempotent ledger and reconciliation."""
import hashlib,hmac,json,os,re,secrets,sqlite3,time
from datetime import date,datetime,timedelta,timezone
from decimal import Decimal
from urllib.request import Request as URLRequest,urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError,URLError
from zoneinfo import ZoneInfo
from fastapi import APIRouter,HTTPException,Request
router=APIRouter();G={};TZ=ZoneInfo('America/Sao_Paulo')
def configure(g):G.update(g)
def stamp():return datetime.now(timezone.utc).isoformat()
def today():return datetime.now(TZ).date()
def configured():return bool(os.getenv('ASAAS_API_KEY') and len(os.getenv('ASAAS_WEBHOOK_TOKEN',''))>=32)

def valid_document(raw):
    value=re.sub(r'\D','',raw or '')
    if len(value) not in (11,14) or len(set(value))==1:return False
    digits=list(map(int,value))
    weights=([10,9,8,7,6,5,4,3,2],[11,10,9,8,7,6,5,4,3,2]) if len(value)==11 else ([5,4,3,2,9,8,7,6,5,4,3,2],[6,5,4,3,2,9,8,7,6,5,4,3,2])
    for i,w in enumerate(weights):
        remainder=sum(x*y for x,y in zip(digits,w))%11;check=0 if remainder<2 else 11-remainder
        if digits[len(w)]!=check:return False
    return True

def initialize(c):
    columns={r[1] for r in c.execute('PRAGMA table_info(professionals)')}
    for key,decl in [('subscription_status',"TEXT NOT NULL DEFAULT 'pending'"),('kyc_status',"TEXT NOT NULL DEFAULT 'pending'"),('subscription_paid',"INTEGER NOT NULL DEFAULT 0")]:
        if key not in columns:c.execute('ALTER TABLE professionals ADD COLUMN '+key+' '+decl)
    c.executescript('''CREATE TABLE IF NOT EXISTS asaas_customers(store_id INTEGER PRIMARY KEY REFERENCES professionals(id),asaas_customer_id TEXT NOT NULL UNIQUE);
    CREATE TABLE IF NOT EXISTS asaas_subscriptions(store_id INTEGER PRIMARY KEY REFERENCES professionals(id),subscription_id TEXT UNIQUE,status TEXT NOT NULL DEFAULT 'pending',price INTEGER NOT NULL,next_due TEXT NOT NULL,updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS webhook_events(event_id TEXT PRIMARY KEY,payload TEXT NOT NULL,processed_at TEXT);
    CREATE TABLE IF NOT EXISTS asaas_payments(payment_id TEXT PRIMARY KEY,store_id INTEGER NOT NULL,due_date TEXT NOT NULL,status TEXT NOT NULL,amount INTEGER NOT NULL,updated_at TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS idx_asaas_payments_store ON asaas_payments(store_id,status,due_date);
    CREATE TABLE IF NOT EXISTS billing_jobs(store_id INTEGER PRIMARY KEY,state TEXT NOT NULL DEFAULT 'pending',attempts INTEGER NOT NULL DEFAULT 0,next_try TEXT NOT NULL DEFAULT '',lease TEXT NOT NULL DEFAULT '',last_error TEXT NOT NULL DEFAULT '');
    CREATE TABLE IF NOT EXISTS billing_runs(name TEXT PRIMARY KEY,last_run TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS kyc_docs(id INTEGER PRIMARY KEY,store_id INTEGER NOT NULL REFERENCES professionals(id),doc_type TEXT NOT NULL,file_path_encrypted TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending',created_at TEXT NOT NULL,reviewed_by TEXT,reviewed_at TEXT);
    CREATE INDEX IF NOT EXISTS idx_kyc_store ON kyc_docs(store_id,status);
    CREATE TABLE IF NOT EXISTS billing_audit(id INTEGER PRIMARY KEY,store_id INTEGER,actor TEXT NOT NULL,action TEXT NOT NULL,created_at TEXT NOT NULL);''')

def audit(c,store,actor,action):c.execute('INSERT INTO billing_audit(store_id,actor,action,created_at) VALUES(?,?,?,?)',(store,actor,action,stamp()))
def effective_status(p):
    p=dict(p)
    allowed=not p.get('blocked') and p.get('is_active',1) and p.get('admission_status')=='approved' and p.get('business_status','open')=='open' and (p.get('subscription_status')=='active' or p.get('subscription_status')=='past_due' and p.get('subscription_paid')) and p.get('kyc_status')=='approved'
    return {'online':bool(allowed),'subscription_status':p.get('subscription_status','pending'),'kyc_status':p.get('kyc_status','pending')}

def assert_available(c,store):
    row=c.execute('SELECT p.*,u.is_active FROM professionals p JOIN users u ON u.id=p.user_id WHERE p.id=?',(store,)).fetchone()
    if not row or not effective_status(row)['online']:raise HTTPException(403,'Loja temporariamente indisponível')

def enqueue(c,store):
    row=c.execute('SELECT document FROM professionals WHERE id=?',(store,)).fetchone()
    if not row or not valid_document(row['document']):raise HTTPException(422,'CPF/CNPJ inválido. Corrija o cadastro antes da aprovação.')
    meta=c.execute("SELECT data FROM adm227_entities WHERE kind='storemeta' AND id=?",(store,)).fetchone();meta=json.loads(meta[0]) if meta else {}
    if meta.get('plan') not in ('start','pro','premium') or not isinstance(meta.get('price'),int) or meta['price']<=0:raise HTTPException(422,'Cadastre plano e preço antes de aprovar a loja.')
    if not configured():raise HTTPException(503,'Configure Asaas no servidor antes de aprovar uma assinatura.')
    c.execute("INSERT INTO billing_jobs(store_id) VALUES(?) ON CONFLICT(store_id) DO UPDATE SET state=CASE WHEN state='done' THEN 'done' ELSE 'pending' END",(store,))

def api(method,path,data=None):
    key=os.getenv('ASAAS_API_KEY','')
    if not key:raise RuntimeError('Asaas não configurado')
    base=os.getenv('ASAAS_API_BASE','https://api-sandbox.asaas.com/v3').rstrip('/')
    if base not in ('https://api-sandbox.asaas.com/v3','https://api.asaas.com/v3'):raise RuntimeError('Endpoint Asaas inválido')
    request=URLRequest(base+path,data=json.dumps(data).encode() if data is not None else None,method=method,headers={'access_token':key,'Content-Type':'application/json','User-Agent':'NowUp/228'})
    try:
        with urlopen(request,timeout=15) as response:return json.load(response)
    except (HTTPError,URLError,TimeoutError):raise RuntimeError('Asaas indisponível; conciliação necessária') from None

def provision(store):
    # Network operations intentionally happen outside SQLite write transactions.
    with connection() as c:
        p=dict(c.execute('SELECT p.*,u.email FROM professionals p JOIN users u ON u.id=p.user_id WHERE p.id=?',(store,)).fetchone())
        if p['admission_status']!='approved':raise RuntimeError('Loja não aprovada')
        meta=json.loads(c.execute("SELECT data FROM adm227_entities WHERE kind='storemeta' AND id=?",(store,)).fetchone()[0])
        existing=c.execute('SELECT * FROM asaas_customers WHERE store_id=?',(store,)).fetchone()
        subscription=c.execute('SELECT * FROM asaas_subscriptions WHERE store_id=?',(store,)).fetchone()
    reference='nowup-store-'+str(store)
    if existing:customer=existing['asaas_customer_id']
    else:
        matches=api('GET','/customers?'+urlencode({'externalReference':reference,'limit':100}))['data']
        matches=[r for r in matches if r.get('externalReference')==reference]
        if len(matches)>1:raise RuntimeError('Clientes duplicados exigem revisão')
        result=matches[0] if matches else api('POST','/customers',{'name':p['display_name'],'cpfCnpj':re.sub(r'\D','',p['document']),'email':p['email'],'externalReference':reference})
        customer=result['id']
        with connection() as c:c.execute('INSERT INTO asaas_customers VALUES(?,?) ON CONFLICT(store_id) DO NOTHING',(store,customer))
    if subscription and subscription['subscription_id']:return
    matches=api('GET','/subscriptions?'+urlencode({'customer':customer,'externalReference':reference,'limit':100}))['data']
    matches=[r for r in matches if r.get('externalReference')==reference and not r.get('deleted')]
    if len(matches)>1:raise RuntimeError('Assinaturas duplicadas exigem revisão')
    result=matches[0] if matches else api('POST','/subscriptions',{'customer':customer,'billingType':'BOLETO','value':str(Decimal(meta['price'])/100),'nextDueDate':p['billing_due_date'] if p['billing_due_date'] and p['billing_due_date']>=today().isoformat() else today().isoformat(),'cycle':'MONTHLY','description':'NowUp '+meta['plan'],'externalReference':reference})
    with connection() as c:
        c.execute("INSERT INTO asaas_subscriptions VALUES(?,?,'pending',?,?,?) ON CONFLICT(store_id) DO NOTHING",(store,result['id'],meta['price'],result['nextDueDate'],stamp()));audit(c,store,'worker','Assinatura criada; aguardando pagamento')

def recompute(c,store,on=None):
    on=on or today();sub=c.execute('SELECT * FROM asaas_subscriptions WHERE store_id=?',(store,)).fetchone()
    if not sub:return
    paid=c.execute("SELECT MAX(due_date) FROM asaas_payments WHERE store_id=? AND status IN ('RECEIVED','CONFIRMED','RECEIVED_IN_CASH')",(store,)).fetchone()[0]
    reversed_due=c.execute("SELECT MAX(due_date) FROM asaas_payments WHERE store_id=? AND status IN ('REFUNDED','DELETED')",(store,)).fetchone()[0]
    if sub['status']=='canceled':status='canceled'
    elif reversed_due and (not paid or reversed_due>=paid):status='blocked'
    else:
        overdue=c.execute("SELECT MIN(due_date) FROM asaas_payments WHERE store_id=? AND status='OVERDUE'",(store,)).fetchone()[0]
        paid=c.execute("SELECT MAX(due_date) FROM asaas_payments WHERE store_id=? AND status IN ('RECEIVED','CONFIRMED','RECEIVED_IN_CASH')",(store,)).fetchone()[0]
        auto=c.execute('SELECT settings FROM adm227_state WHERE id=1').fetchone();auto=json.loads(auto[0]).get('autoBlock',True) if auto else True
        status=('blocked' if auto and (on-date.fromisoformat(overdue)).days>=4 else 'past_due') if overdue else 'active' if paid else 'pending'
    c.execute('UPDATE asaas_subscriptions SET status=?,updated_at=? WHERE store_id=?',(status,stamp(),store));c.execute('UPDATE professionals SET subscription_status=?,subscription_paid=? WHERE id=?',(status,int(bool(paid)),store))
    # Manual moderation blocking is separate and is never undone by a payment.

def apply_event(c,event):
    name=event.get('event','');payment=event.get('payment') or {};subscription=event.get('subscription') or {}
    supported={'PAYMENT_RECEIVED','PAYMENT_CONFIRMED','PAYMENT_OVERDUE','PAYMENT_REFUNDED','PAYMENT_DELETED','SUBSCRIPTION_CANCELED','SUBSCRIPTION_DELETED','SUBSCRIPTION_INACTIVATED'}
    if name not in supported:return True
    sid=payment.get('subscription') or subscription.get('id');sub=c.execute('SELECT * FROM asaas_subscriptions WHERE subscription_id=?',(sid,)).fetchone()
    if not sub:return False
    store=sub['store_id']
    if name in ('SUBSCRIPTION_CANCELED','SUBSCRIPTION_DELETED','SUBSCRIPTION_INACTIVATED'):
        c.execute("UPDATE asaas_subscriptions SET status='canceled',updated_at=? WHERE store_id=?",(stamp(),store));recompute(c,store);audit(c,store,'asaas',name);return True
    states={'PAYMENT_RECEIVED':'RECEIVED','PAYMENT_CONFIRMED':'CONFIRMED','PAYMENT_OVERDUE':'OVERDUE','PAYMENT_REFUNDED':'REFUNDED','PAYMENT_DELETED':'DELETED'}
    if name not in states:return True
    if not payment.get('id') or not payment.get('dueDate'):raise ValueError('Evento de pagamento incompleto')
    date.fromisoformat(payment['dueDate']);status=states[name]
    old=c.execute('SELECT status FROM asaas_payments WHERE payment_id=?',(payment['id'],)).fetchone()
    # A late OVERDUE webhook must not undo a confirmed receipt for the same invoice.
    if old and old['status'] in ('RECEIVED','CONFIRMED','RECEIVED_IN_CASH','REFUNDED','DELETED') and status=='OVERDUE':return True
    amount=int(Decimal(str(payment.get('value',0)))*100)
    if amount<0:raise ValueError('Valor inválido')
    if old and old['status'] in ('REFUNDED','DELETED') and status in ('RECEIVED','CONFIRMED'):return True
    if status in ('RECEIVED','CONFIRMED') and amount!=sub['price']:raise ValueError('Pagamento diverge do contrato; requer conciliação')
    c.execute('INSERT INTO asaas_payments VALUES(?,?,?,?,?,?) ON CONFLICT(payment_id) DO UPDATE SET status=excluded.status,amount=excluded.amount,updated_at=excluded.updated_at',(payment['id'],store,payment['dueDate'],status,amount,stamp()))
    recompute(c,store);audit(c,store,'asaas',name);return True

@router.post('/webhooks/asaas')
async def webhook(request:Request):
    secret=os.getenv('ASAAS_WEBHOOK_TOKEN','')
    if len(secret)<32 or not hmac.compare_digest(request.headers.get('asaas-access-token',''),secret):raise HTTPException(401,'Webhook não autorizado')
    raw=await request.body()
    if len(raw)>1000000:raise HTTPException(413,'Payload acima do limite')
    try:
        event=json.loads(raw);eid=event['id']
        if not isinstance(eid,str) or not 1<=len(eid)<=200:raise ValueError()
    except (ValueError,KeyError,AssertionError,TypeError):raise HTTPException(422,'Evento inválido')
    with connection() as c:
        c.execute('BEGIN IMMEDIATE')
        if c.execute('SELECT 1 FROM webhook_events WHERE event_id=?',(eid,)).fetchone():return {'ok':True,'duplicate':True}
        c.execute('INSERT INTO webhook_events VALUES(?,?,NULL)',(eid,json.dumps(event)))
        try:done=apply_event(c,event)
        except (ValueError,KeyError,TypeError):raise HTTPException(422,'Evento inconsistente; revisão necessária')
        if done:c.execute('UPDATE webhook_events SET processed_at=? WHERE event_id=?',(stamp(),eid))
        c.commit()
    G.get('invalidate',lambda:None)();return {'ok':True,'queued':not done}

def reconcile(store):
    with connection() as c:sub=dict(c.execute('SELECT * FROM asaas_subscriptions WHERE store_id=?',(store,)).fetchone())
    live=api('GET','/subscriptions/'+sub['subscription_id'])
    if live.get('deleted') or live.get('status')=='INACTIVE':
        with connection() as c:apply_event(c,{'event':'SUBSCRIPTION_DELETED','subscription':{'id':sub['subscription_id']}})
        return
    payments=[];offset=0
    while True:
        page=api('GET','/subscriptions/'+sub['subscription_id']+'/payments?'+urlencode({'limit':100,'offset':offset}));payments.extend(page['data'])
        if not page.get('hasMore'):break
        offset+=100
    with connection() as c:
        for p in payments:
            status=p['status'];due=p['dueDate'];date.fromisoformat(due)
            # Pending invoice already past D0 becomes delinquent even if a webhook was lost.
            if status=='PENDING' and due<today().isoformat():status='OVERDUE'
            c.execute('INSERT INTO asaas_payments VALUES(?,?,?,?,?,?) ON CONFLICT(payment_id) DO UPDATE SET status=excluded.status,amount=excluded.amount,updated_at=excluded.updated_at',(p['id'],store,due,status,int(Decimal(str(p['value']))*100),stamp()))
        c.execute('UPDATE asaas_subscriptions SET next_due=? WHERE store_id=?',(live['nextDueDate'],store));recompute(c,store)

def tick():
    # Run in a single scheduler process. A file lock is taken by the CLI/embedded worker.
    with connection() as c:
        jobs=[r['store_id'] for r in c.execute("SELECT store_id FROM billing_jobs WHERE state!='done' AND next_try<=? AND lease<=? LIMIT 25",(stamp(),stamp()))]
    for store in jobs:
        with connection() as c:
            changed=c.execute("UPDATE billing_jobs SET lease=?,state='running',attempts=attempts+1 WHERE store_id=? AND lease<=?",((datetime.now(timezone.utc)+timedelta(minutes=10)).isoformat(),store,stamp())).rowcount
        if not changed:continue
        try:
            provision(store)
            with connection() as c:c.execute("UPDATE billing_jobs SET state='done',lease='',last_error='' WHERE store_id=?",(store,))
        except Exception:
            with connection() as c:c.execute("UPDATE billing_jobs SET state='retry',lease='',next_try=?,last_error='Falha na integração; conferir conciliação' WHERE store_id=?",((datetime.now(timezone.utc)+timedelta(minutes=15)).isoformat(),store))
    with connection() as c:
        for r in c.execute('SELECT event_id,payload FROM webhook_events WHERE processed_at IS NULL LIMIT 100').fetchall():
            try:
                if apply_event(c,json.loads(r['payload'])):c.execute('UPDATE webhook_events SET processed_at=? WHERE event_id=?',(stamp(),r['event_id']))
            except (ValueError,KeyError,TypeError):continue
        for r in c.execute('SELECT store_id FROM asaas_subscriptions').fetchall():recompute(c,r['store_id'])
        run=c.execute("SELECT last_run FROM billing_runs WHERE name='reconcile'").fetchone()
        ids=[r[0] for r in c.execute('SELECT store_id FROM asaas_subscriptions')] if not run or run[0][:10]!=today().isoformat() else []
    all_ok=True
    for store in ids:
        try:reconcile(store)
        except Exception:all_ok=False
    if ids and all_ok:
        with connection() as c:c.execute("INSERT INTO billing_runs VALUES('reconcile',?) ON CONFLICT(name) DO UPDATE SET last_run=excluded.last_run",(stamp(),))
    G.get('invalidate',lambda:None)()

from contextlib import contextmanager
@contextmanager
def connection():
    c=G['db']()
    try:
        yield c;c.commit()
    except Exception:c.rollback();raise
    finally:c.close()

@router.post('/admin/super/api/billing/{store}/provision')
async def activate_existing(request:Request,store:int):
    G['admin'].csrf(request)
    try:body=await request.json()
    except ValueError:raise HTTPException(422,'Conteúdo inválido')
    reason=body.get('reason','') if isinstance(body,dict) else ''
    if not isinstance(reason,str) or len(reason.strip())<8:raise HTTPException(422,'Informe uma justificativa')
    with connection() as c:
        actor=G['admin'].auth(request,c,'finance')
        if not actor['super'] and 'finance' not in actor['permissions']:raise HTTPException(403,'Permissão de escrita de Financeiro necessária')
        p=c.execute('SELECT admission_status FROM professionals WHERE id=?',(store,)).fetchone()
        if not p or p[0]!='approved':raise HTTPException(409,'Aprove o cadastro da loja antes de ativar cobrança')
        enqueue(c,store);audit(c,store,actor['actor_id'],'Provisionamento solicitado: '+reason[:500])
    return {'ok':True,'state':'queued','note':'A cobrança é criada pelo worker; este retorno não confirma pagamento.'}

# Stable business-rule entry point for callers and acceptance checks.
get_effective_status=effective_status
