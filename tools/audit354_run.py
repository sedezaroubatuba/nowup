"""Reproducible catalogue audit; loopback server and disposable SQLite only.
Never import this module into production. Outbound email is captured locally.
"""
import asyncio,io,json,os,sqlite3,statistics,subprocess,sys,tempfile,threading,time,traceback
from pathlib import Path
from datetime import datetime,timedelta,timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));os.chdir(ROOT)
RUN=Path(os.environ.get('NOWUP_AUDIT_DIR',tempfile.mkdtemp(prefix='nowup354-'))).resolve();RUN.mkdir(exist_ok=True,parents=True)
os.environ.update(NOWUP_DB_ENGINE='sqlite',NOWUP_DB=str(RUN/'audit.db'),NOWUP_UPLOAD_DIR=str(RUN/'uploads'),NOWUP_ADMIN_EMAIL='audit354@example.com',NOWUP_ADMIN_PASSWORD='Isolated-audit354-password',NOWUP_HTTPS='0')
for name in ['DATABASE_URL','NOWUP_PUBLIC_ORIGIN','BREVO_API_KEY','SMTP_PASSWORD','SMTP_HOST','NOWUP_TEST_SANDBOX333']:os.environ.pop(name,None)
import app as m
from email_validator import validate_email,EmailNotValidError
from fastapi import Request
import uvicorn,httpx
from PIL import Image
RESULT={'run_dir':str(RUN),'engine':'sqlite','outbound_email':'stubbed; DNS deliverability disabled only in harness','checks':[],'loads':[]}
def check(name,ok,detail=''):
 RESULT['checks'].append({'name':name,'ok':bool(ok),'detail':detail});print(name,ok,str(detail)[:180],flush=True)
def email(value):
 try:return validate_email(value,check_deliverability=False).normalized.lower()
 except EmailNotValidError:return None
m.normalize_email=email;m.email_service_configured=lambda:True
mail_lock=threading.Lock()
def sent(*args,**kw):
 with mail_lock:
  with (RUN/'emails.jsonl').open('a') as f:f.write(json.dumps({'args':args,'kwargs':kw})+'\n')
 return True
m.send_email=sent;m.send_verification=lambda *args:sent(*args)
for callback in m.app.router.on_startup:
 if callback.__name__!='start':callback()
import socket
sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
BASE=f'http://127.0.0.1:{port}';os.environ['NOWUP_BASE_URL']=BASE
server=uvicorn.Server(uvicorn.Config(m.app,host='127.0.0.1',port=port,log_level='error',lifespan='off',access_log=False))
thread=threading.Thread(target=server.run,daemon=True);thread.start()
for _ in range(200):
 if server.started:break
 time.sleep(.05)
client=httpx.Client(trust_env=False,base_url=BASE,headers={'Origin':BASE},timeout=40,follow_redirects=False)
stores=[];customers=[];expiry=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
photo=io.BytesIO();Image.new('RGB',(1200,900),'purple').save(photo,'JPEG');photo=photo.getvalue()
try:
 for i in range(50):
  payload=dict(name=f'Loja Auditoria354 {i:02}',email=f'merchant354-{i}@example.com',phone='12999999999',password='Merchant354-password',password_confirm='Merchant354-password',accept_terms='1',business_type='store',offer_mode='catalog' if i%2 else 'menu',plan='cardapio',city='São Sebastião' if i%2 else 'Ubatuba',neighborhood='Centro',address='Rua de teste, 100',state='SP')
  r=client.post('/cadastro/profissional',data=payload)
  with m.db() as c:
   p=c.execute('SELECT p.* FROM professionals p JOIN users u ON u.id=p.user_id WHERE u.email=?',(payload['email'],)).fetchone()
   if not p:raise RuntimeError(f'Merchant {i}: {r.status_code} {r.headers.get("location")} {r.text[:100]}')
   p=dict(p);token=f'isolated-merchant354-{i}'
   c.execute("UPDATE users SET email_verified=1 WHERE id=?",(p['user_id'],))
   c.execute("UPDATE professionals SET plan_active='cardapio',admission_status='approved',blocked=0,is_premium=1,plan_requested='',business_status='open',business_hours='',allows_pickup=1,allows_delivery=1,delivery_fee_cents=500,minimum_order_cents=0 WHERE id=?",(p['id'],))
   c.execute('INSERT INTO sessions(token,user_id,expires_at) VALUES(?,?,?)',(token,p['user_id'],expiry))
   c.execute("INSERT INTO store_menu257(professional_id,whatsapp,mode) VALUES(?,'5512999999999','whatsapp')",(p['id'],))
  merchant=httpx.Client(trust_env=False,base_url=BASE,headers={'Origin':BASE,'Cookie':'nowup_session='+token},timeout=40)
  r=merchant.post('/painel/cardapio/produtos',data={'name':f'Produto foto {i}','price':'12,50','category':'Bebidas','available':'1','extras_mode':'none'},files={'photo':('foto.jpg',photo,'image/jpeg')})
  if r.status_code!=303:raise RuntimeError(f'Product {i}: {r.status_code} {r.text[:100]}')
  with m.db() as c:
   product=dict(c.execute('SELECT * FROM products WHERE professional_id=? ORDER BY id DESC LIMIT 1',(p['id'],)).fetchone())
   assert (m.UPLOAD_DIR/product['image_filename']).exists()
   for j in range(19):c.execute("INSERT INTO products(professional_id,name,category,price_cents,available,created_at,updated_at,image_filename,extras_mode) VALUES(?,?,?,1250,1,?,?,?,'none')",(p['id'],f'Produto {j} loja {i}','Bebidas' if j%2 else 'Alimentos',m.now_iso(),m.now_iso(),product['image_filename']))
   for j in range(2):
    n=i*2+j;uid=c.execute("INSERT INTO users(role,name,email,phone,password_hash,email_verified,created_at,customer_store345,customer_email345,address,neighborhood,city,state) VALUES('customer',?,?,?,'unused-for-session-load',1,?,?,?,?,?,'Ubatuba','SP')",(f'Cliente {n}',f'load-internal354-{n}@example.com','12988888888',m.now_iso(),p['id'],f'load354-{n}@example.com','Rua teste 10','Centro')).lastrowid
    tok=f'isolated-customer354-{n}';c.execute('INSERT INTO sessions(token,user_id,expires_at,store_id345) VALUES(?,?,?,?)',(tok,uid,expiry,p['id']))
    customers.append({'store':p['id'],'slug':p['slug'],'product':product['id'],'token':tok,'uid':uid})
  stores.append({'id':p['id'],'slug':p['slug'],'merchant_token':token,'product':product['id'],'photo':product['image_filename']});merchant.close()
 check('50 merchant registrations and product photo uploads',len(stores)==50)
 check('100 verified scoped customers',len(customers)==100)
 with m.db() as c:
  check('1000 catalogue products',c.execute('SELECT COUNT(*) FROM products WHERE professional_id IN ('+','.join('?'*50)+')',tuple(s['id'] for s in stores)).fetchone()[0]==1000)
  before_orders=c.execute('SELECT COUNT(*) FROM orders').fetchone()[0]
 async def burst(label,count,kind):
  burst_started=time.perf_counter();start=asyncio.Event()
  async with httpx.AsyncClient(trust_env=False,base_url=BASE,limits=httpx.Limits(max_connections=count,max_keepalive_connections=count),timeout=60) as ac:
   async def one(n):
    await start.wait();u=customers[n%100];t=time.perf_counter()
    try:
     headers={'Origin':BASE,'Cookie':f"nowup_loja345_{u['store']}={u['token']}"}
     if kind=='checkout':
      r=await ac.post('/p/'+u['slug']+'/menu/whatsapp',headers=headers,data={'customer_name':'Nome adulterado','customer_phone':'12988888888','cart_json':json.dumps([{'id':u['product'],'quantity':2,'price':1}]),'fulfillment_type':'pickup','payment_method':'pix','request_key':f'audit354-{label}-{n:04}'})
      d=r.json();ok=r.status_code==200 and d.get('prepared') and not d.get('recorded') and d.get('total_cents')==2500 and d.get('whatsapp_url','').startswith('https://wa.me/5512999999999?text=') and f'Cliente {n%100}' in d.get('message','')
     else:r=await ac.get('/p/'+u['slug']+'/menu?loja=1',headers=headers);ok=r.status_code==200 and 'data-native-menu' in r.text
     return {'status':r.status_code,'ms':round((time.perf_counter()-t)*1000,2),'ok':bool(ok),'detail':r.text[:140] if not ok else ''}
    except Exception as e:return {'status':0,'ms':round((time.perf_counter()-t)*1000,2),'ok':False,'detail':repr(e)}
   tasks=[asyncio.create_task(one(n)) for n in range(count)];await asyncio.sleep(.05);start.set();rows=await asyncio.gather(*tasks)
  values=sorted(x['ms'] for x in rows);result={'label':label,'requests':count,'kind':kind,'concurrency':count,'ok':sum(x['ok'] for x in rows),'errors':[x for x in rows if not x['ok']],'p50_ms':statistics.median(values),'p95_ms':values[max(0,int(len(values)*.95)-1)],'max_ms':max(values),'elapsed_s':round(time.perf_counter()-burst_started,3)};RESULT['loads'].append(result);print('LOAD',json.dumps(result),flush=True)
 for label,n,kind in [('warmup',10,'checkout'),('50-lojas-100-pedidos',100,'checkout'),('100-navegadores',100,'browse'),('segunda-rajada',100,'checkout')]:asyncio.run(burst(label,n,kind))
 with m.db() as c:check('WhatsApp-only does not invent internal orders',c.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==before_orders)
 # Tenant and input boundaries through the real HTTP stack.
 a,b=customers[0],customers[2]
 header={'Origin':BASE,'Cookie':f"nowup_loja345_{a['store']}={a['token']}"}
 body={'customer_name':'Cliente','customer_phone':'12988888888','cart_json':json.dumps([{'id':b['product'],'quantity':1}]),'request_key':'cross-store354-00001'}
 r=client.post('/p/'+a['slug']+'/menu/whatsapp',headers=header,data=body);check('Foreign product rejected',r.status_code==400,r.status_code)
 r=client.post('/p/'+b['slug']+'/menu/whatsapp',headers=header,data={**body,'request_key':'cross-account354-0001'});check('Foreign store session rejected',r.status_code==401,r.status_code)
 for path in ['/painel','/painel/kanban228','/painel/vendas-manuais/relatorios']:
  r=client.get(path,headers={'Cookie':'nowup_session='+stores[0]['merchant_token']});check('Merchant page '+path,r.status_code==200,r.status_code)
 manifest={'base':BASE,'run_dir':str(RUN),'stores':stores,'customers':customers,'results':RESULT}
 (RUN/'manifest.json').write_text(json.dumps(manifest));(RUN/'results.json').write_text(json.dumps(RESULT,indent=2))
 print('READY_FOR_BROWSER',RUN/'manifest.json',flush=True)
 # Explicit bounded window for the companion browser audit, not a background service.
 until=time.time()+1800
 def browser():
  with (RUN/'browser.log').open('w') as log:subprocess.run(['node',str(ROOT/'tools/audit354_browser.cjs'),str(RUN/'manifest.json')],stdout=log,stderr=subprocess.STDOUT,timeout=900,env={**os.environ,'AUDIT_PYTHON':sys.executable})
 browser()
 while not (RUN/'stop').exists() and time.time()<until:
  if (RUN/'rerun').exists():
   (RUN/'rerun').unlink();browser()
  time.sleep(.5)
except Exception:
 traceback.print_exc();(RUN/'results.json').write_text(json.dumps(RESULT,indent=2));raise
finally:client.close();server.should_exit=True;thread.join(timeout=10)
