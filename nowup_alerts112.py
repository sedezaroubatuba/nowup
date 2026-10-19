import os
"""Customer alerts: private incremental polling and persistent push jobs."""
import json,time,threading,logging,hashlib
from contextlib import contextmanager
from fastapi import APIRouter,Request,HTTPException
import nowup_push75 as push
from nowup_sales107 import check_origin
router=APIRouter();_stop=threading.Event();_thread=None

def configure(db,auth):
    global _db,_auth
    _db,_auth=db,auth

@contextmanager
def connection():
    c=_db()
    try:
        with c:yield c
    finally:c.close()

def initialize():
    with connection() as c:c.execute('CREATE TABLE IF NOT EXISTS customer_push112(id INTEGER PRIMARY KEY,event_id INTEGER NOT NULL UNIQUE,user_id INTEGER NOT NULL,payload TEXT NOT NULL,created REAL NOT NULL,next_try REAL NOT NULL,attempts INTEGER NOT NULL DEFAULT 0)')

def enqueue(c,uid,event_id,payload):
    c.execute('INSERT OR IGNORE INTO customer_push112(event_id,user_id,payload,created,next_try) VALUES(?,?,?,?,?)',(event_id,uid,json.dumps(payload,ensure_ascii=False),time.time(),time.time()))

@router.get('/cliente/avisos')
def updates(request:Request,after:int=-1):
    u=_auth(request,'customer')
    with connection() as c:
        latest=c.execute('SELECT COALESCE(MAX(id),0) FROM notifications WHERE user_id=?',(u['id'],)).fetchone()[0]
        rows=[] if after<0 else [dict(x) for x in c.execute('SELECT id,title,message,link,created_at FROM notifications WHERE user_id=? AND id>? ORDER BY id LIMIT 50',(u['id'],after))]
        orders=[dict(x) for x in c.execute("SELECT id,status,order_code,tracking_token FROM orders WHERE customer_id=? ORDER BY id DESC LIMIT 50",(u['id'],))]
    return {'cursor':latest if after<0 else rows[-1]['id'] if rows else after,'notifications':rows,'orders':orders}

@router.get('/cliente/push/config')
def config(request:Request):
    _auth(request,'customer');return {'publicKey':push.keys()[1]}

@router.post('/cliente/push/ativar')
async def activate(request:Request):
    check_origin(request);u=_auth(request,'customer')
    try:data=push.validate(await request.json())
    except (ValueError,TypeError,AttributeError):raise HTTPException(400,'Inscrição inválida.')
    with connection() as c:
        c.execute('BEGIN IMMEDIATE');old=c.execute('SELECT user_id FROM push_subscriptions WHERE endpoint=?',(data['endpoint'],)).fetchone()
        if old and old['user_id']!=u['id']:raise HTTPException(409,'Desative os avisos da conta anterior neste aparelho.')
        if not old and c.execute('SELECT COUNT(*) FROM push_subscriptions WHERE user_id=?',(u['id'],)).fetchone()[0]>=10:raise HTTPException(400,'Limite de aparelhos atingido.')
        c.execute('INSERT OR REPLACE INTO push_subscriptions VALUES(?,?,?,?)',(data['endpoint'],u['id'],push.session(request),json.dumps(data)))
    return {'ok':True}

@router.post('/cliente/push/desativar')
def deactivate(request:Request):
    check_origin(request);_auth(request,'customer');push.disable_session(request.cookies.get('nowup_session',''));return {'ok':True}

@router.post('/cliente/push/testar')
def test(request:Request):
    check_origin(request);u=_auth(request,'customer')
    with connection() as c:rows=c.execute('SELECT * FROM push_subscriptions WHERE user_id=? AND session_hash=?',(u['id'],push.session(request))).fetchall()
    if not rows:raise HTTPException(400,'Ative os avisos neste aparelho primeiro.')
    if not all(push.send(r,{'title':'NowUp','body':'Avisos ativados neste aparelho.','url':'/cliente','tag':'nowup-teste'}) for r in rows):raise HTTPException(502,'Não foi possível enviar. Tente novamente.')
    return {'ok':True}

def process():
    now=time.time()
    with connection() as c:
        c.execute('BEGIN IMMEDIATE');c.execute('DELETE FROM customer_push112 WHERE created<? OR attempts>=6',(now-3600,))
        job=c.execute('SELECT * FROM customer_push112 WHERE next_try<=? ORDER BY id LIMIT 1',(now,)).fetchone()
        if not job:return
        c.execute('UPDATE customer_push112 SET next_try=?,attempts=attempts+1 WHERE id=?',(now+60,job['id']))
        rows=c.execute('SELECT * FROM push_subscriptions WHERE user_id=?',(job['user_id'],)).fetchall()
    success=True
    for row in rows:success=push.send(row,json.loads(job['payload'])) and success
    if success:
        with connection() as c:c.execute('DELETE FROM customer_push112 WHERE id=?',(job['id'],))

def run():
    while not _stop.is_set():
        try:process()
        except Exception:logging.warning('NowUp: aviso de status aguardando nova tentativa.')
        _stop.wait(3)

def start():
    global _thread
    initialize()
    if os.getenv("NOWUP_TEST_MODE")=="1":return
    _stop.clear();_thread=threading.Thread(target=run,daemon=True);_thread.start()
def stop():_stop.set()
