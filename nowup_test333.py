"""Private administrator playground: separate process, SQLite and uploads.

No production rows or credentials enter the child. All child network connections
are denied. The production session is checked before every proxied request.
"""
from __future__ import annotations
import atexit
import asyncio
import base64
import json
import select
import struct
import hashlib
import html
import http.client
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import threading
import time
from http.cookies import SimpleCookie
from fastapi import Request, Form

PREFIX = '/admin/modo-teste'
MODE_COOKIE = 'nowup_test333'
COOKIE_PREFIX = 'nu333_'
HOP = {'connection','transfer-encoding','content-length','content-encoding','keep-alive','upgrade','te','trailer'}


def child_environment(directory, secret):
    # An allowlist prevents production DB, mail, R2, Redis and payment keys
    # from leaking into the sandbox, including future integration variables.
    env = {k: v for k, v in os.environ.items() if k in (
        'PATH','PYTHONPATH','VIRTUAL_ENV','LANG','LC_ALL','TZ','LD_LIBRARY_PATH')}
    env['PYTHONPATH']=os.pathsep.join(str(Path(p).resolve()) for p in sys.path if p)
    env.update(NOWUP_TEST_CHILD333='1', NOWUP_TEST_SECRET333=secret,
        NOWUP_DB_ENGINE='sqlite', NOWUP_DB=str(directory / 'nowup.db'),
        NOWUP_UPLOAD_DIR=str(directory / 'uploads'),
        NOWUP_ADMIN_EMAIL='admin@teste.nowup.local',
        NOWUP_ADMIN_PASSWORD=secrets.token_urlsafe(40),
        NOWUP_BACKUP_ENABLED='0', HOME=str(directory), TMPDIR=str(directory))
    return env


class Playground:
    def __init__(self, base, directory):
        self.base, self.directory = base, directory
        self.secret = secrets.token_urlsafe(40)
        self.process = None
        self.lock = threading.Lock()
        self.ipc_lock = threading.Lock()
    def start(self):
        with self.lock:
            if self.process and self.process.poll() is None:
                return
            self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            self.process = subprocess.Popen(
                [sys.executable, str(self.base / 'nowup_test333.py'), '--child'],
                cwd=str(self.base), env=child_environment(self.directory,self.secret),
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL)
            for _ in range(300):
                if self.process.poll() is not None:
                    raise RuntimeError('Não foi possível iniciar o ambiente de teste.')
                try:
                    status, _, _ = self.request('GET','/__ready333',[],b'')
                    if status == 200: return
                except (OSError,http.client.HTTPException): pass
                time.sleep(.1)
            self.close()
            raise RuntimeError('O ambiente de teste demorou para iniciar. Tente novamente.')
    def request(self, method, path, headers, body):
        payload=json.dumps({'method':method,'path':path,'headers':headers,
            'body':base64.b64encode(body).decode()}).encode()
        with self.ipc_lock:
            if not self.process or self.process.poll() is not None: raise OSError('Test process stopped')
            self.process.stdin.write(struct.pack('!I',len(payload))+payload)
            self.process.stdin.flush()
            def read_exact(size):
                chunks=[]
                while size:
                    if not select.select([self.process.stdout],[],[],45)[0]: raise OSError('Test response timed out')
                    chunk=os.read(self.process.stdout.fileno(),min(size,65536))
                    if not chunk: raise OSError('Test process stopped')
                    chunks.append(chunk); size-=len(chunk)
                return b''.join(chunks)
            length=struct.unpack('!I',read_exact(4))[0]
            if length>64*1024*1024: raise OSError('Test response too large')
            result=json.loads(read_exact(length))
            return result['status'],result['headers'],base64.b64decode(result['body'])
    def close(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try: self.process.wait(timeout=5)
            except subprocess.TimeoutExpired: self.process.kill(); self.process.wait()


def install(G):
    if os.getenv('NOWUP_TEST_CHILD333') == '1': return
    from fastapi import Request
    from fastapi.responses import HTMLResponse, RedirectResponse, Response
    from starlette.concurrency import run_in_threadpool
    app=G['app']; instances={}; tickets={}; lock=threading.Lock()
    root=Path(tempfile.mkdtemp(prefix='nowup-private-test333-'))
    atexit.register(lambda: [p.close() for p in instances.values()])

    def production_admin(request):
        return G['require_user'](request,'admin')
    def secure(request): return request.url.scheme=='https' or os.getenv('NOWUP_HTTPS')=='1'
    def ticket_key(request):
        return hashlib.sha256(request.cookies.get('nowup_session','').encode()).hexdigest()

    @app.get(PREFIX, response_class=HTMLResponse)
    def home(request: Request):
        production_admin(request)
        return HTMLResponse('''<!doctype html><html lang="pt-BR"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Modo de teste · NowUp</title><body style="font:16px system-ui;background:#f5f3ff;color:#30154f;margin:0;padding:32px"><main style="max-width:620px;margin:auto;background:white;padding:28px;border-radius:20px"><h1>🧪 Modo de teste</h1><p>Use o NowUp como administrador, lojista e cliente. Cadastre lojas, escolha planos, monte o cardápio e faça pedidos de teste.</p><p>Banco de dados e fotos separados. Sem cobranças, mensagens externas ou participação nas estatísticas reais.</p><form method="post" action="/admin/modo-teste/entrar"><button style="background:#7136bf;color:white;border:0;border-radius:12px;padding:16px;font:inherit">Abrir NowUp em teste</button></form><p>Para contratar um plano de verdade, saia do teste e faça a contratação no ambiente real. Os testes não são convertidos automaticamente.</p><a href="/admin/super">Voltar ao ADM</a></main></body></html>''',headers={'Cache-Control':'private, no-store'})

    @app.post(PREFIX+'/entrar')
    async def enter(request: Request):
        user=production_admin(request)
        with lock:
            playground=instances.setdefault(user['id'],Playground(G['BASE'],root/str(user['id'])))
        try:
            await run_in_threadpool(playground.start)
            status,headers,_=await run_in_threadpool(playground.request,'POST','/__login333',
                [('Host',request.headers.get('host','localhost')),('Origin',str(request.base_url).rstrip('/')),('X-Forwarded-Proto',request.url.scheme),('X-Test-Secret333',playground.secret)],b'')
            if status != 303: raise RuntimeError('Falha ao abrir a sessão de teste.')
        except (OSError,RuntimeError,http.client.HTTPException):
            return HTMLResponse('Não foi possível abrir o teste. <a href="'+PREFIX+'">Tentar novamente</a>',status_code=503)
        ticket=secrets.token_urlsafe(40)
        # One active playground authorization per production session.
        for old,value in list(tickets.items()):
            if value[1]==ticket_key(request): tickets.pop(old,None)
        tickets[ticket]=(user['id'],ticket_key(request))
        response=RedirectResponse('/__controle333',303)
        response.set_cookie(MODE_COOKIE,ticket,httponly=True,secure=secure(request),samesite='strict',max_age=1800)
        copy_cookies(headers,response)
        return response

    @app.post(PREFIX+'/sair')
    def leave(request: Request):
        tickets.pop(request.cookies.get(MODE_COOKIE,''),None)
        response=RedirectResponse('/admin/super',303)
        response.delete_cookie(MODE_COOKIE)
        for name in request.cookies:
            if name.startswith(COOKIE_PREFIX): response.delete_cookie(name)
        return response

    @app.middleware('http')
    async def route_playground(request: Request, call_next):
        mode=request.cookies.get(MODE_COOKIE)
        if not mode and (request.headers.get('x-nowup-test333')=='1' or request.query_params.get('__nu333_test')=='1'):
            return Response('O teste foi encerrado. Reabra o modo de teste no ADM.',status_code=409)
        if not mode or request.url.path.startswith(PREFIX):
            return await call_next(request)
        user=G['current_user'](request)
        if not user or user['role']!='admin' or tickets.get(mode)!=(user['id'],ticket_key(request)):
            return HTMLResponse('O acesso ao teste expirou. <form method="post" action="'+PREFIX+'/sair"><button>Voltar ao NowUp real</button></form>',status_code=403,headers={'Cache-Control':'no-store'})
        playground=instances.get(user['id'])
        if not playground or not playground.process or playground.process.poll() is not None:
            return HTMLResponse('O teste foi encerrado. <form method="post" action="'+PREFIX+'/sair"><button>Voltar ao ADM</button></form>',status_code=503)
        # Prevent a production service worker from being installed by a test page.
        if request.headers.get('service-worker')=='script':
            return Response(status_code=404,headers={'Cache-Control':'no-store'})
        cookies=SimpleCookie()
        for name,value in request.cookies.items():
            if name.startswith(COOKIE_PREFIX): cookies[name[len(COOKIE_PREFIX):]]=value
        headers=[(k,v) for k,v in request.headers.items() if k.lower() not in HOP|{'cookie','accept-encoding','x-test-secret333','x-forwarded-proto'}]
        headers.extend([('Cookie',cookies.output(header='',sep=';').strip()),('Accept-Encoding','identity'),('X-Forwarded-Proto',request.url.scheme)])
        path=request.url.path+('?' + request.url.query if request.url.query else '')
        body_parts=[]; body_size=0
        async for chunk in request.stream():
            body_size+=len(chunk)
            if body_size>25*1024*1024:
                return Response('Envio acima do limite permitido.',status_code=413)
            body_parts.append(chunk)
        try:
            status,received,body=await run_in_threadpool(playground.request,request.method,path,headers,b''.join(body_parts))
        except (OSError,http.client.HTTPException):
            return HTMLResponse('O teste está indisponível. <form method="post" action="'+PREFIX+'/sair"><button>Voltar ao ADM</button></form>',status_code=503)
        response=Response(body,status_code=status)
        for key,value in received:
            if key.lower() not in HOP|{'set-cookie','cache-control'}: response.headers.append(key,value)
        response.headers['Cache-Control']='private, no-store'
        copy_cookies(received,response)
        return response


def copy_cookies(headers,response):
    for key,value in headers:
        if key.lower()!='set-cookie': continue
        cookie=SimpleCookie(); cookie.load(value)
        for name,morsel in cookie.items():
            name2=COOKIE_PREFIX+name
            cookie2=SimpleCookie(); cookie2[name2]=morsel.value
            for attribute in ('path','expires','max-age','httponly','secure','samesite'):
                if morsel[attribute]: cookie2[name2][attribute]=morsel[attribute]
            response.headers.append('set-cookie',cookie2[name2].OutputString())


def child_main():
    # Process-wide network guard applies to future payment/email integrations too.
    def audit(event,args):
        if event in ('socket.connect','socket.getaddrinfo'):
            raise PermissionError('Modo de teste: conexões externas desativadas.')
        if event in ('subprocess.Popen','os.system','os.posix_spawn'):
            raise PermissionError('Modo de teste: processos externos desativados.')
    sys.addaudithook(audit)
    import mailing
    mailing.send_email=lambda *a,**k: True
    mailing.send_verification=lambda *a,**k: True
    mailing.configured=lambda: True
    import app as main
    main.email_service_configured=lambda: True
    from fastapi import Request, Form
    from fastapi.responses import HTMLResponse, RedirectResponse, Response
    app=main.app

    @app.get('/__ready333')
    def ready(): return {'ready':True}

    @app.post('/__login333')
    def login(request: Request):
        if not secrets.compare_digest(request.headers.get('x-test-secret333',''),os.environ['NOWUP_TEST_SECRET333']):
            return Response(status_code=403)
        with main.db() as c:
            user=c.execute("SELECT id FROM users WHERE role='admin' ORDER BY id LIMIT 1").fetchone()
        return main.create_session_response(user['id'],'/__controle333',True)

    @app.get('/__controle333',response_class=HTMLResponse)
    def control():
        with main.db() as c:
            users=c.execute("SELECT id,name,role FROM users WHERE is_active=1 ORDER BY id").fetchall()
        options=''.join('<option value="'+str(u['id'])+'">'+html.escape(u['name']+' ('+u['role']+')')+'</option>' for u in users)
        return HTMLResponse('<html lang="pt-BR"><meta name="viewport" content="width=device-width, initial-scale=1"><body style="font:16px system-ui;padding:24px"><h1>🧪 NowUp em teste</h1><p>Escolha como navegar. Todos os dados desta área são de teste.</p><p><a href="/cadastro/profissional">Cadastrar loja</a> · <a href="/cadastro/cliente">Cadastrar cliente</a> · <a href="/">Ver NowUp</a></p><form method="post" action="/__perfil333"><label>Acessar como <select name="uid">'+options+'</select></label> <button>Abrir conta de teste</button></form><h2>Criar loja de teste rapidamente</h2><form method="post" action="/__loja333"><label>Nome <input name="name" required maxlength="120" value="Minha loja de teste"></label><label> Plano <select name="plan"><option value="cardapio">Cardápio</option><option value="vitrine">Vitrine</option><option value="ambos">Vitrine + cardápio</option></select></label><label> Tipo <select name="offer"><option value="menu">Cardápio de alimentação</option><option value="catalog">Catálogo de produtos</option></select></label><button>Criar e acessar loja</button></form><p>Este atalho não exige documentos ou pagamento. Para conferir o formulário completo, use Cadastrar loja.</p><p>Cadastros de teste têm e-mail confirmado e plano liberado automaticamente. Use dados fictícios.</p></body></html>')

    @app.post('/__loja333')
    def create_store(name: str=Form(...),plan: str=Form(...),offer: str=Form('menu')):
        if plan not in ('vitrine','cardapio','ambos') or offer not in ('menu','catalog') or not name.strip():
            return Response(status_code=400)
        offer='services' if plan=='vitrine' else offer
        with main.db() as c:
            email='teste-'+secrets.token_hex(10)+'@example.com'
            uid=c.execute("INSERT INTO users(role,name,email,phone,password_hash,is_active,email_verified,created_at) VALUES('professional',?,?,?, ?,1,1,?)",(name.strip()[:120],email,'12999990000',main.hash_password(secrets.token_urlsafe(32)),main.now_iso())).lastrowid
            pid=c.execute("INSERT INTO professionals(user_id,slug,display_name,doc_type,document,whatsapp,city,neighborhood,address,state,description,services,business_type,offer_mode,plan_active,admission_status,verified,blocked,is_premium,plan_granted,created_at) VALUES(?,?,?,'CNPJ','','12999990000','Ubatuba','Centro','Endereço fictício de teste','SP','','','store',?,?,'approved',1,0,1,1,?)",(uid,main.unique_slug(c,name),name.strip()[:120],offer,plan,main.now_iso())).lastrowid
            cat=c.execute('SELECT id FROM categories WHERE active=1 ORDER BY sort_order,id LIMIT 1').fetchone()
            if cat: c.execute('INSERT INTO professional_categories(professional_id,category_id) VALUES(?,?)',(pid,cat[0]))
            c.commit()
        return main.create_session_response(uid,'/painel')

    @app.post('/__perfil333')
    def switch(uid: int=Form(...)):
        with main.db() as c: user=c.execute('SELECT * FROM users WHERE id=? AND is_active=1',(uid,)).fetchone()
        if not user: return Response(status_code=404)
        dest={'admin':'/admin/super','professional':'/painel','customer':'/cliente'}[user['role']]
        return main.create_session_response(uid,dest,user['role']=='admin')

    @app.middleware('http')
    async def simulated(request: Request,call_next):
        response=await call_next(request)
        # Only the child's independent database is ever changed here.
        if request.method=='POST' and not request.url.path.startswith('/__'):
            with main.db() as c:
                c.execute('UPDATE users SET email_verified=1')
                c.execute("UPDATE professionals SET verified=1,blocked=0,admission_status='approved',plan_granted=1,plan_active=CASE WHEN plan_requested IN ('vitrine','cardapio','ambos') THEN plan_requested WHEN plan_active='none' THEN 'ambos' ELSE plan_active END,is_premium=1,offer_mode=CASE WHEN plan_requested_offer IN ('menu','catalog') THEN plan_requested_offer ELSE offer_mode END,plan_requested='',plan_requested_offer=''")
                c.commit()
            if request.url.path in ('/cadastro/cliente','/cadastro/profissional') and response.headers.get('location')=='/cadastro/aguardando':
                return RedirectResponse('/__controle333',303)
        if 'text/html' not in response.headers.get('content-type',''): return response
        body=b''.join([chunk async for chunk in response.body_iterator])
        browser_guard=b'<script src="/static/test333-guard.js"></script>'
        head_start=body.lower().find(b'<head')
        head_end=body.find(b'>',head_start) if head_start>=0 else -1
        body=body[:head_end+1]+browser_guard+body[head_end+1:] if head_end>=0 else browser_guard+body
        banner=b'''<aside style="position:sticky;top:0;z-index:2147483647;background:#7136bf;color:white;padding:12px;font:14px system-ui;display:flex;gap:14px;flex-wrap:wrap;align-items:center"><b>TESTE - sem cobrancas e fora das estatisticas reais</b><a style="color:white" href="/__controle333">Trocar perfil / cadastrar loja</a><form method="post" action="/admin/modo-teste/sair" style="margin:0"><button>Sair do teste</button></form></aside>'''
        marker=body.lower().find(b'<body')
        end=body.find(b'>',marker) if marker>=0 else -1
        body=body[:end+1]+banner+body[end+1:] if end>=0 else banner+body
        headers={k:v for k,v in response.headers.items() if k.lower() not in HOP|{'set-cookie','cache-control'}}
        result=Response(body,status_code=response.status_code,headers=headers)
        for key,value in response.headers.raw:
            if key.lower()==b'set-cookie': result.raw_headers.append((key,value))
        result.headers['Cache-Control']='private, no-store'
        return result
    protocol_in=sys.stdin.buffer; protocol_out=sys.stdout.buffer
    sys.stdout=sys.stderr
    async def serve():
        async with app.router.lifespan_context(app):
            while True:
                head=await asyncio.to_thread(protocol_in.read,4)
                if not head: return
                size=struct.unpack('!I',head)[0]
                if size>40*1024*1024: return
                packet=json.loads(await asyncio.to_thread(protocol_in.read,size))
                path,_,query=packet['path'].partition('?')
                headers=[(k.lower().encode('latin1'),v.encode('latin1')) for k,v in packet['headers']]
                scheme=dict(headers).get(b'x-forwarded-proto',b'http').decode()
                scope={'type':'http','asgi':{'version':'3.0','spec_version':'2.4'},
                    'http_version':'1.1','method':packet['method'],'scheme':scheme,
                    'path':path,'raw_path':path.encode(),'query_string':query.encode(),
                    'root_path':'','headers':headers,'server':('localhost',80),
                    'client':('127.0.0.1',0)}
                sent=[]; delivered=False; finished=asyncio.Event()
                async def receive():
                    nonlocal delivered
                    if not delivered:
                        delivered=True
                        return {'type':'http.request','body':base64.b64decode(packet['body']),'more_body':False}
                    await finished.wait()
                    return {'type':'http.disconnect'}
                async def send(message):
                    sent.append(message)
                    if message['type']=='http.response.body' and not message.get('more_body',False): finished.set()
                try:
                    await app(scope,receive,send)
                    start=next(m for m in sent if m['type']=='http.response.start')
                    result={'status':start['status'],'headers':[(k.decode('latin1'),v.decode('latin1')) for k,v in start['headers']],
                        'body':base64.b64encode(b''.join(m.get('body',b'') for m in sent if m['type']=='http.response.body')).decode()}
                except Exception:
                    import traceback
                    traceback.print_exc()
                    result={'status':500,'headers':[('Content-Type','text/plain')],
                        'body':base64.b64encode('Erro no ambiente de teste. Os dados reais não foram alterados.'.encode()).decode()}
                encoded=json.dumps(result).encode()
                protocol_out.write(struct.pack('!I',len(encoded))+encoded); protocol_out.flush()
    asyncio.run(serve())


if __name__=='__main__':
    if os.getenv('NOWUP_TEST_CHILD333')!='1': raise SystemExit('Private test process only')
    child_main()
