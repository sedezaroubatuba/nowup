"""Private per-session Web Push subscriptions; durable order delivery queue."""
from contextlib import contextmanager
import base64, hashlib, json, logging, re, threading, time
from urllib.parse import urlsplit
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from pywebpush import webpush, WebPushException
router=APIRouter()
_stop=threading.Event()
_thread=None

def configure(db, auth):
    global _db, _auth
    @contextmanager
    def connection():
        c=db()
        try:
            with c: yield c
        finally: c.close()
    _db, _auth=connection, auth

def initialize():
    with _db() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS push_settings(id INTEGER PRIMARY KEY, private_key TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS push_subscriptions(endpoint TEXT PRIMARY KEY,user_id INTEGER NOT NULL,session_hash TEXT NOT NULL,subscription TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS push_jobs(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL,order_id INTEGER NOT NULL UNIQUE,created REAL NOT NULL,next_try REAL NOT NULL,attempts INTEGER NOT NULL DEFAULT 0);''')
        key=ec.generate_private_key(ec.SECP256R1())
        encoded=base64.urlsafe_b64encode(key.private_bytes(serialization.Encoding.DER,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())).decode()
        c.execute('INSERT OR IGNORE INTO push_settings VALUES(1,?)',(encoded,))

def keys():
    with _db() as c: private=c.execute('SELECT private_key FROM push_settings WHERE id=1').fetchone()[0]
    key=serialization.load_der_private_key(base64.urlsafe_b64decode(private),None)
    public=base64.urlsafe_b64encode(key.public_key().public_bytes(serialization.Encoding.X962,serialization.PublicFormat.UncompressedPoint)).decode().rstrip('=')
    return private, public

def session(request):
    return hashlib.sha256(request.cookies.get('nowup_session','').encode()).hexdigest()

def disable_session(token):
    with _db() as c: c.execute('DELETE FROM push_subscriptions WHERE session_hash=?',(hashlib.sha256(token.encode()).hexdigest(),))

def validate(data):
    endpoint=data.get('endpoint',''); parts=urlsplit(endpoint)
    host=parts.hostname or ''
    allowed=host in ('fcm.googleapis.com','updates.push.services.mozilla.com','web.push.apple.com') or host.endswith('.notify.windows.com')
    if not allowed or parts.scheme!='https' or parts.username or parts.password or parts.port not in (None,443) or parts.fragment or len(endpoint)>2048:
        raise HTTPException(400,'Serviço de avisos não reconhecido.')
    result={'endpoint':endpoint,'keys':{}}
    for name,length in [('p256dh',65),('auth',16)]:
        value=data.get('keys',{}).get(name,'')
        if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_-]+={0,2}',value): raise HTTPException(400,'Inscrição inválida.')
        try: decoded=base64.urlsafe_b64decode(value+'='*(-len(value)%4))
        except Exception: raise HTTPException(400,'Inscrição inválida.')
        if len(decoded)!=length: raise HTTPException(400,'Inscrição inválida.')
        if name=='p256dh':
            try: ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(),decoded)
            except ValueError: raise HTTPException(400,'Inscrição inválida.')
        result['keys'][name]=value
    return result

@router.get('/painel/push/config')
def config(request:Request):
    _auth(request,'professional')
    return {'publicKey':keys()[1]}

@router.post('/painel/push/ativar')
async def subscribe(request:Request):
    u=_auth(request,'professional')
    try: data=validate(await request.json())
    except (ValueError,TypeError,AttributeError): raise HTTPException(400,'Inscrição inválida.')
    with _db() as c:
        c.execute('BEGIN IMMEDIATE')
        existing=c.execute('SELECT user_id FROM push_subscriptions WHERE endpoint=?',(data['endpoint'],)).fetchone()
        if existing and existing[0]!=u['id']: raise HTTPException(409,'Desative os avisos da conta anterior neste aparelho.')
        count=c.execute('SELECT count(*) FROM push_subscriptions WHERE user_id=?',(u['id'],)).fetchone()[0]
        if not existing and count>=10: raise HTTPException(400,'Limite de 10 aparelhos atingido.')
        c.execute('INSERT OR REPLACE INTO push_subscriptions VALUES(?,?,?,?)',(data['endpoint'],u['id'],session(request),json.dumps(data)))
    return {'ok':True}

@router.post('/painel/push/desativar')
def unsubscribe(request:Request):
    _auth(request,'professional'); disable_session(request.cookies.get('nowup_session','')); return {'ok':True}

def send(row,payload):
    try:
        webpush(json.loads(row['subscription']),json.dumps(payload),vapid_private_key=keys()[0],vapid_claims={'sub':'https://nowup-i9n4.onrender.com'},ttl=3600,timeout=10)
        return True
    except WebPushException as exc:
        status=exc.response.status_code if exc.response is not None else getattr(exc,'status_code',None)
        if status in (404,410):
            with _db() as c: c.execute('DELETE FROM push_subscriptions WHERE endpoint=?',(row['endpoint'],))
            return True
        logging.warning('NowUp push: serviço recusou envio (status %s).',status)
        return False
    except Exception:
        logging.warning('NowUp push: falha no envio.'); return False

@router.post('/painel/push/testar')
def test(request:Request):
    u=_auth(request,'professional')
    with _db() as c: rows=c.execute('SELECT * FROM push_subscriptions WHERE user_id=? AND session_hash=?',(u['id'],session(request))).fetchall()
    if not rows: raise HTTPException(400,'Ative os avisos primeiro.')
    ok=all(send(row,{'title':'Avisos do NowUp','body':'Teste de aviso neste aparelho.','url':'/painel','tag':'nowup-teste'}) for row in rows)
    if not ok: raise HTTPException(502,'Não foi possível enviar o teste. Tente novamente.')
    return {'ok':True}

def enqueue_on_connection(c,user_id,order_id):
    c.execute('INSERT OR IGNORE INTO push_jobs(user_id,order_id,created,next_try) VALUES(?,?,?,?)',(user_id,order_id,time.time(),time.time()))

def process():
    now=time.time()
    with _db() as c:
        c.execute('BEGIN IMMEDIATE')
        c.execute('DELETE FROM push_jobs WHERE created<? OR attempts>=4',(now-3600,))
        job=c.execute('SELECT * FROM push_jobs WHERE next_try<=? ORDER BY id LIMIT 1',(now,)).fetchone()
        if not job:return
        c.execute('UPDATE push_jobs SET next_try=?,attempts=attempts+1 WHERE id=?',(now+120,job['id']))
        rows=c.execute('SELECT * FROM push_subscriptions WHERE user_id=?',(job['user_id'],)).fetchall()
    payload={'title':'Novo pedido no NowUp','body':'Sua loja recebeu um pedido. Abra o painel para conferir.','url':f"/painel#pedido-{job['order_id']}",'tag':f"nowup-pedido-{job['order_id']}"}
    success=True
    for row in rows: success=send(row,payload) and success
    if success:
        with _db() as c:c.execute('DELETE FROM push_jobs WHERE id=?',(job['id'],))

def run():
    while not _stop.is_set():
        try: process()
        except Exception: logging.warning('NowUp push: fila aguardando nova tentativa.')
        _stop.wait(5)

def start():
    global _thread
    initialize(); _stop.clear(); _thread=threading.Thread(target=run,daemon=True); _thread.start()
def stop():_stop.set()

@router.get('/nowup-push-sw.js')
def worker():
    from pathlib import Path
    return Response((Path(__file__).parent/'static'/'nowup-push-sw.js').read_text(),media_type='application/javascript',headers={'Cache-Control':'no-cache','Service-Worker-Allowed':'/'})
