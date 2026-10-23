"""HTTP and database acceptance tests. No network calls or production credentials."""
import hashlib,json,secrets,sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import date,datetime,timedelta,timezone
import pytest
from fastapi.testclient import TestClient
from test_merchant228 import env

@pytest.fixture
def release(env):
 m,_,_,pid,other=env
 now=m.now_iso();expires=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()
 admin_token=secrets.token_hex(24);buyer_token=secrets.token_hex(24)
 with m.db() as c:
  for table in ('asaas_payments','asaas_subscriptions','asaas_customers','billing_jobs'):
   c.execute('DELETE FROM '+table+' WHERE store_id=?',(pid,))
  admin=c.execute("SELECT id FROM users WHERE role='admin'").fetchone()[0]
  buyer=c.execute("INSERT INTO users(role,name,email,password_hash,is_active,email_verified,created_at) VALUES('customer','Buyer',?,'invalid',1,1,?)",(secrets.token_hex(10)+'@test.invalid',now)).lastrowid
  for token,uid in ((admin_token,admin),(buyer_token,buyer)):c.execute('INSERT INTO sessions VALUES(?,?,?)',(token,uid,expires))
  c.execute("UPDATE professionals SET is_demo=0,blocked=0,admission_status='approved',business_status='open',business_hours='',plan_active='ambos',is_premium=1,offer_mode='menu',subscription_status='active',subscription_paid=1,kyc_status='approved' WHERE id=?",(pid,))
  slug=c.execute('SELECT slug FROM professionals WHERE id=?',(pid,)).fetchone()[0]
  product=c.execute("INSERT INTO products(professional_id,name,category,price_cents,available,max_quantity,created_at,updated_at) VALUES(?,'Produto','Geral',3000,1,99,?,?)",(pid,now,now)).lastrowid
  c.commit()
 client=TestClient(m.app,base_url='https://testserver',headers={'origin':'https://testserver','x-nowup-admin':'227'},follow_redirects=False);client.cookies.set('nowup_session',admin_token)
 customer=TestClient(m.app,base_url='https://testserver',headers={'origin':'https://testserver'},follow_redirects=False);customer.cookies.set('nowup_session',buyer_token)
 return m,client,customer,pid,slug,product,admin_token,buyer

def test_logout_revokes_legacy_and_super_tabs(release):
 m,admin,_,_,_,_,token,_=release
 assert admin.get('/admin/super/api/state').status_code==200
 assert admin.get('/admin/legado').status_code==200
 r=admin.post('/admin/super/api/logout');assert r.status_code==200 and r.json()['next']=='/entrar?logout=ok'
 assert 'HttpOnly' in str(r.headers.get_list('set-cookie')) and 'Secure' in str(r.headers.get_list('set-cookie'))
 admin.cookies.set('nowup_session',token)
 assert admin.get('/admin/super/api/state').status_code==401
 assert admin.get('/admin/legado').status_code==401
 with m.db() as c:assert c.execute('SELECT revoked_at FROM adm227_access WHERE token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),)).fetchone()[0]
 assert admin.post('/logout').headers['location']=='/entrar?logout=ok'

def test_marketing_has_no_customers_or_orders(release):
 m,admin,_,_,_,_,_,_=release
 token=secrets.token_hex(24)
 with m.db() as c:
  sid=m.nowup_admin227.nextid(c,'staff');m.nowup_admin227.put(c,'staff',sid,{'id':sid,'name':'Marketing','email':'marketing@test.invalid','enabled':True,'permissions':['marketing'],'role':'Marketing'})
  c.execute('INSERT INTO adm227_team_sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),sid,(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()));c.commit()
 admin.cookies.clear();admin.cookies.set('nowup_team227',token,path='/admin/super')
 r=admin.get('/admin/super/api/state');assert r.status_code==200,r.text
 assert r.json()['orders']==[] and r.json()['customers']==[]
 assert admin.get('/admin/super/api/orders').status_code==403
 assert admin.get('/admin/super/api/customers').status_code==403

def test_checkout_concurrency_and_server_prices(release):
 m,_,buyer,pid,slug,product,_,uid=release
 key=secrets.token_hex(24);data={'customer_name':'Buyer','customer_phone':'12999999999','fulfillment_type':'pickup','cart_json':json.dumps([{'id':product,'quantity':1,'price_cents':1}])}
 def send(_):return buyer.post('/p/'+slug+'/menu/pedido',data=data,headers={'X-Idempotency-Key':key})
 with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(send,range(2)))
 assert [r.status_code for r in responses]==[303,303],[r.text for r in responses]
 assert responses[0].headers['location']==responses[1].headers['location']
 with m.db() as c:
  rows=c.execute('SELECT total_cents,delivery_neighborhood FROM orders WHERE customer_id=?',(uid,)).fetchall();assert len(rows)==1 and rows[0][0]==3000
  assert c.execute('SELECT COUNT(*) FROM idempotency_keys WHERE store_id=? AND key=?',(pid,key)).fetchone()[0]==1
 assert buyer.post('/p/'+slug+'/menu/pedido',data=data).status_code==400
 assert buyer.post('/p/'+slug+'/menu/pedido',data={**data,'customer_name':'Changed'},headers={'X-Idempotency-Key':key}).status_code==409

def test_overnight_sql_and_history(release):
 m,admin,_,pid,_,_,_,uid=release
 with m.db() as c:
  for local in ('2026-10-22T18:00:00-03:00','2026-10-23T01:59:00-03:00','2026-10-23T02:59:00-03:00'):
   t=datetime.fromisoformat(local).astimezone(timezone.utc).isoformat()
   c.execute("INSERT INTO orders(professional_id,customer_id,customer_name,status,total_cents,created_at,updated_at,delivery_neighborhood) VALUES(?,?,'Turno','completed',1000,?,?,'Centro histórico')",(pid,uid,t,t))
  c.commit()
 q={'from':'2026-10-22','to':'2026-10-22','hour_from':'18','hour_to':'2','store':pid,'q':'Turno'}
 m.nowup_data228.invalidate();r=admin.get('/admin/super/api/metrics',params=q);assert r.status_code==200,r.text
 assert r.json()['count']==2 and r.json()['gmv']==2000
 q.pop('hour_from');q.pop('hour_to');q.update({'from':'2026-10-23','to':'2026-10-23'})
 rows=admin.get('/admin/super/api/orders',params=q).json()['items'];assert any(o['hour']==2 and o['minute']==59 and o['neighborhood']=='Centro histórico' for o in rows)
 assert admin.get('/admin/super/api/orders?limit=500').status_code==422

def test_kyc_checks_private_upload_review_and_expiry(release,monkeypatch):
 m,admin,_,pid,_,_,_,_=release
 from nowup_billing228 import valid_document
 assert not valid_document('00000000000000') and not valid_document('11111111111')
 assert valid_document('11222333000181') and valid_document('52998224725')
 monkeypatch.setenv('NOWUP_KYC_DIR',str(m.DB_PATH.parent/'private'))
 with m.db() as c:c.execute("UPDATE professionals SET document='11222333000181' WHERE id=?",(pid,));c.commit()
 for kind in ('identity','business'):
  r=admin.post('/api/stores/'+str(pid)+'/kyc',data={'doc_type':kind},files={'file':('doc.pdf',b'%PDF-1.4 isolated test','application/pdf')});assert r.status_code==200,r.text
 doc=r.json()['id'];url=admin.get('/api/kyc/'+str(doc)+'/url');assert url.status_code==200
 signed=url.json()['url'];assert admin.get(signed).content==b'%PDF-1.4 isolated test'
 assert admin.get(signed.replace('signature=','signature=invalid')).status_code==403
 r=admin.post('/api/stores/'+str(pid)+'/kyc/review',json={'status':'approved','reason':'Documentos conferidos manualmente'});assert r.status_code==200,r.text
 with m.db() as c:
  row=c.execute('SELECT * FROM kyc_docs WHERE id=?',(doc,)).fetchone();assert row['status']=='approved' and 'private' not in row['file_path_encrypted']
  assert c.execute('SELECT kyc_status FROM professionals WHERE id=?',(pid,)).fetchone()[0]=='approved'

def test_billing_duplicate_webhook_grace_block_and_reactivate(release,monkeypatch):
 m,admin,buyer,pid,slug,_,_,_=release
 token='isolated-webhook-token-00000000000000000';monkeypatch.setenv('ASAAS_WEBHOOK_TOKEN',token)
 import nowup_billing228 as b
 sid='sub_'+secrets.token_hex(8)
 with m.db() as c:
  c.execute("INSERT INTO asaas_subscriptions VALUES(?,?,'pending',7900,?,?)",(pid,sid,b.today().isoformat(),b.stamp()));c.commit()
 def event(name,payment,due):return {'id':secrets.token_hex(16),'event':name,'payment':{'id':payment,'subscription':sid,'value':79,'dueDate':due}}
 old=(b.today()-timedelta(days=35)).isoformat();past=(b.today()-timedelta(days=5)).isoformat()
 received=event('PAYMENT_RECEIVED','old_'+sid,old)
 for _ in range(2):assert admin.post('/webhooks/asaas',json=received,headers={'asaas-access-token':token}).status_code==200
 overdue=event('PAYMENT_OVERDUE','late_'+sid,past)
 assert admin.post('/webhooks/asaas',json=overdue,headers={'asaas-access-token':token}).status_code==200
 with m.db() as c:
  assert c.execute('SELECT COUNT(*) FROM webhook_events WHERE event_id=?',(received['id'],)).fetchone()[0]==1
  assert c.execute('SELECT subscription_status FROM professionals WHERE id=?',(pid,)).fetchone()[0]=='blocked'
  b.recompute(c,pid,date.fromisoformat(past)+timedelta(days=3));assert c.execute('SELECT subscription_status FROM professionals WHERE id=?',(pid,)).fetchone()[0]=='past_due'
  b.recompute(c,pid);c.commit()
 assert buyer.get('/p/'+slug).status_code==403
 paid=event('PAYMENT_RECEIVED','late_'+sid,past);assert admin.post('/webhooks/asaas',json=paid,headers={'asaas-access-token':token}).status_code==200
 with m.db() as c:assert c.execute('SELECT subscription_status FROM professionals WHERE id=?',(pid,)).fetchone()[0]=='active'
 assert admin.post('/webhooks/asaas',json=paid,headers={'asaas-access-token':'wrong'}).status_code==401
 # A delayed overdue notification cannot undo settlement for the same invoice.
 delayed=event('PAYMENT_OVERDUE','late_'+sid,past);admin.post('/webhooks/asaas',json=delayed,headers={'asaas-access-token':token})
 with m.db() as c:assert c.execute('SELECT subscription_status FROM professionals WHERE id=?',(pid,)).fetchone()[0]=='active'

def test_secret_boot_requirements(monkeypatch):
 from nowup_security import require_secrets
 monkeypatch.delenv('NOWUP_ADMIN_SECRET',raising=False)
 with pytest.raises(RuntimeError,match='NOWUP_ADMIN_SECRET'):require_secrets()

def test_cart_sync_is_owned_by_customer(release):
 _,admin,buyer,pid,_,product,_,_=release
 payload={'items':[['one',{'productId':product,'name':'Product','quantity':1}]],'updatedAt':datetime.now(timezone.utc).timestamp()*1000}
 assert buyer.put('/api/cart/'+str(pid),json=payload).status_code==200
 assert buyer.get('/api/cart/'+str(pid)).json()['items']==payload['items']
 assert admin.get('/api/cart/'+str(pid)).status_code==401

def test_approval_queues_subscription_and_provider_is_retry_safe(release,monkeypatch):
 m,_,_,pid,_,_,_,_=release
 import nowup_billing228 as b
 monkeypatch.setenv('ASAAS_API_KEY','isolated-test-key');monkeypatch.setenv('ASAAS_WEBHOOK_TOKEN','isolated-test-hook-token-000000000000000')
 with m.db() as c:
  c.execute("UPDATE professionals SET document='11222333000181' WHERE id=?",(pid,))
  m.nowup_admin227.put(c,'storemeta',pid,{'id':pid,'plan':'start','price':7900})
  b.enqueue(c,pid);b.enqueue(c,pid);c.commit()
 customer={};subscription={};calls=[]
 def fake(method,path,data=None):
  calls.append((method,path))
  if method=='GET' and path.startswith('/customers?'):return {'data':list(customer.values())}
  if method=='POST' and path=='/customers':
   customer['one']={'id':'customer-test','externalReference':data['externalReference']};return customer['one']
  if method=='GET' and path.startswith('/subscriptions?'):return {'data':list(subscription.values())}
  if method=='POST' and path=='/subscriptions':
   subscription['one']={'id':'subscription-test','externalReference':data['externalReference'],'nextDueDate':data['nextDueDate']};return subscription['one']
  raise AssertionError((method,path))
 monkeypatch.setattr(b,'api',fake)
 b.provision(pid);b.provision(pid)
 assert calls.count(('POST','/customers'))==1 and calls.count(('POST','/subscriptions'))==1
 with m.db() as c:
  assert c.execute('SELECT COUNT(*) FROM billing_jobs WHERE store_id=?',(pid,)).fetchone()[0]==1
  assert c.execute('SELECT status FROM asaas_subscriptions WHERE store_id=?',(pid,)).fetchone()[0]=='pending'

def test_reconciliation_finds_missing_overdue_and_paid_events(release,monkeypatch):
 m,_,_,pid,_,_,_,_=release
 import nowup_billing228 as b
 sid=secrets.token_hex(12);due=(b.today()-timedelta(days=5)).isoformat()
 with m.db() as c:c.execute("INSERT INTO asaas_subscriptions VALUES(?,?,'pending',7900,?,?)",(pid,sid,due,b.stamp()));c.commit()
 state=['PENDING']
 def fake(method,path,data=None):
  if path.endswith('/'+sid):return {'nextDueDate':due,'status':'ACTIVE'}
  return {'data':[{'id':'reconcile-'+sid,'value':79,'dueDate':due,'status':state[0]}],'hasMore':False}
 monkeypatch.setattr(b,'api',fake)
 b.reconcile(pid)
 with m.db() as c:assert c.execute('SELECT subscription_status FROM professionals WHERE id=?',(pid,)).fetchone()[0]=='blocked'
 state[0]='RECEIVED';b.reconcile(pid);b.reconcile(pid)
 with m.db() as c:
  assert c.execute('SELECT subscription_status FROM professionals WHERE id=?',(pid,)).fetchone()[0]=='active'
  assert c.execute('SELECT COUNT(*) FROM asaas_payments WHERE store_id=?',(pid,)).fetchone()[0]==1

def test_read_only_store_role_cannot_approve_kyc(release):
 m,admin,_,pid,_,_,_,_=release
 token=secrets.token_hex(24)
 with m.db() as c:
  sid=m.nowup_admin227.nextid(c,'staff');m.nowup_admin227.put(c,'staff',sid,{'id':sid,'name':'Read only','email':'readonly@test.invalid','role':'Analyst','enabled':True,'permissions':['stores:read']})
  c.execute('INSERT INTO adm227_team_sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),sid,(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()));c.commit()
 admin.cookies.clear();admin.cookies.set('nowup_team227',token,path='/')
 assert admin.post('/api/stores/'+str(pid)+'/kyc/review',json={'status':'approved','reason':'Attempt by read only role'}).status_code==403

def test_bounded_products_and_mutation(release):
 m,admin,_,pid,_,product,_,_=release
 rows=admin.get('/admin/super/api/products',params={'store':pid}).json()['items']
 assert any(p['id']==product for p in rows) and len(rows)<=50
 state=admin.get('/admin/super/api/state').json()
 assert state['orders']==[] and state['customers']==[] and state['products']==[]
 r=admin.post('/admin/super/api/change',json={'revision':state['_meta']['revision'],'reason':'Produto pausado para conferência administrativa','changes':[{'kind':'products','id':product,'value':{'status':'Pausado'}}]})
 assert r.status_code==200,r.text
 with m.db() as c:assert c.execute('SELECT available FROM products WHERE id=?',(product,)).fetchone()[0]==0

def test_failed_db_responds_friendly_503(release,monkeypatch):
 m,admin,_,_,_,_,_,_=release
 def broken():raise sqlite3.OperationalError('secret-db-path-do-not-expose')
 monkeypatch.setitem(m.nowup_data228.G,'db',broken)
 r=admin.get('/admin/super/api/metrics');assert r.status_code==503
 assert 'secret-db-path' not in r.text and 'temporariamente' in r.text

def test_current_refund_does_not_keep_store_active(release,monkeypatch):
 m,admin,_,pid,_,_,_,_=release
 import nowup_billing228 as b
 token='isolated-refund-webhook-token-000000000000';monkeypatch.setenv('ASAAS_WEBHOOK_TOKEN',token)
 sid=secrets.token_hex(12);due=b.today().isoformat()
 with m.db() as c:c.execute("INSERT INTO asaas_subscriptions VALUES(?,?,'pending',7900,?,?)",(pid,sid,due,b.stamp()));c.commit()
 def send(kind):return admin.post('/webhooks/asaas',json={'id':secrets.token_hex(16),'event':kind,'payment':{'id':'pay-'+sid,'subscription':sid,'value':79,'dueDate':due}},headers={'asaas-access-token':token})
 assert send('PAYMENT_RECEIVED').status_code==200
 assert send('PAYMENT_REFUNDED').status_code==200
 assert send('PAYMENT_RECEIVED').status_code==200
 with m.db() as c:assert c.execute('SELECT subscription_status FROM professionals WHERE id=?',(pid,)).fetchone()[0]=='blocked'
