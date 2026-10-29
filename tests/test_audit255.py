"""Regression tests against disposable SQLite data; never use a live database."""
import json
from datetime import datetime,timezone,timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import sqlite3
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from test_checkout247 import checkout
import nowup_admin227 as admin

@pytest.mark.parametrize('field,value',[('fulfillment_type','invalid'),('payment_method','invalid'),('payment_method','<script>')])
def test_unknown_checkout_choices_rejected(checkout,field,value):
 m,client,url,data,_,_=checkout;data[field]=value
 assert client.post(url,data=data,follow_redirects=False).status_code==400
 with m.db() as c:assert c.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==0

def test_price_comes_from_server_and_promo_is_applied(checkout):
 m,client,url,data,pid,_=checkout
 with m.db() as c:c.execute('UPDATE products SET price_cents=1000,promo_price_cents=750 WHERE id=?',(pid,))
 data['cart_json']=json.dumps([{'id':pid,'quantity':2,'price':1,'unitPrice':1}])
 r=client.post(url,data=data,follow_redirects=False);assert r.status_code==303,r.text
 with m.db() as c:assert c.execute('SELECT total_cents FROM orders').fetchone()[0]==1500

@pytest.mark.parametrize('blocked', ['blocked','closed','owner_disabled','product_disabled','other_store'])
def test_store_and_product_boundaries(checkout,blocked):
 m,client,url,data,pid,_=checkout
 with m.db() as c:
  pro=c.execute('SELECT professional_id FROM products WHERE id=?',(pid,)).fetchone()[0]
  if blocked=='blocked':c.execute('UPDATE professionals SET blocked=1 WHERE id=?',(pro,))
  elif blocked=='closed':c.execute("UPDATE professionals SET business_status='temporarily_closed' WHERE id=?",(pro,))
  elif blocked=='owner_disabled':c.execute('UPDATE users SET is_active=0 WHERE id=(SELECT user_id FROM professionals WHERE id=?)',(pro,))
  elif blocked=='product_disabled':c.execute('UPDATE products SET available=0 WHERE id=?',(pid,))
  else:c.execute('UPDATE products SET professional_id=(SELECT id FROM professionals WHERE id<>? LIMIT 1) WHERE id=?',(pro,pid))
 r=client.post(url,data=data,follow_redirects=False)
 assert r.status_code in (303,400,404,409)
 if r.status_code==303:assert 'fechado=1' in r.headers['location']
 with m.db() as c:assert c.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==0

def test_variants_cannot_bypass_product_quantity_limit(checkout):
 m,client,url,data,pid,_=checkout
 with m.db() as c:c.execute('UPDATE products SET max_quantity=2 WHERE id=?',(pid,))
 data['cart_json']=json.dumps([{'id':pid,'quantity':2},{'id':pid,'quantity':1,'notes':'different'}])
 assert client.post(url,data=data,follow_redirects=False).status_code==400

def test_rollback_after_order_insert_keeps_no_partial_order(checkout,monkeypatch):
 m,_,url,data,_,_=checkout
 original=m.nowup_push75.enqueue_on_connection
 def fail(*args):raise RuntimeError('simulated local failure')
 monkeypatch.setattr(m.nowup_push75,'enqueue_on_connection',fail)
 client=TestClient(m.app,headers={'Origin':'http://testserver'},raise_server_exceptions=False)
 assert client.post(url,data=data,follow_redirects=False).status_code==500
 with m.db() as c:
  assert c.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==0
  assert c.execute('SELECT COUNT(*) FROM order_items').fetchone()[0]==0
  assert c.execute('SELECT COUNT(*) FROM checkout_requests229').fetchone()[0]==0
 monkeypatch.setattr(m.nowup_push75,'enqueue_on_connection',original)
 assert client.post(url,data=data,follow_redirects=False).status_code==303

@pytest.mark.parametrize('value',['false',0,1,None,{},[]])
def test_staff_state_requires_boolean(value):
 with pytest.raises(HTTPException) as e:admin.validate_staff255({'enabled':value,'permissions':['orders']})
 assert e.value.status_code==400

@pytest.mark.parametrize('value',[None,'orders',[{}],[1],['unknown'],['orders','orders']])
def test_staff_permissions_fail_cleanly(value):
 with pytest.raises(HTTPException) as e:admin.validate_staff255({'enabled':True,'permissions':value})
 assert e.value.status_code==400

@pytest.fixture
def panel(checkout,monkeypatch):
 m,_,_,_,_,_=checkout
 m.nowup_admin227.initialize()
 m.nowup_home210.configure(vars(m))
 actor={'id':1,'role':'admin','name':'Auditor','email':'audit@example.invalid'}
 monkeypatch.setitem(admin.G,'current_user',lambda request:actor)
 client=TestClient(m.app,headers={'Origin':'http://testserver','X-Nowup-Admin':'227'})
 client.cookies.set('nowup_session','local-admin-session')
 return m,client,actor

def test_staff_disable_revokes_sessions_codes_and_invites(panel):
 m,client,_=panel
 with m.db() as c:
  admin.put(c,'staff',1,{'id':1,'name':'Team','email':'team@example.invalid','enabled':True,'permissions':['orders']})
  c.execute('INSERT INTO adm227_team_sessions VALUES(?,?,?)',('session',1,'2099'))
  c.execute('INSERT INTO adm227_challenges VALUES(?,?,?,?,?)',('challenge',1,'hash','2099',0))
  c.execute('INSERT INTO adm227_invites VALUES(?,?,?)',('invite',1,'2099'))
 rev=client.get('/admin/super/api/state').json()['_meta']['revision']
 result=client.post('/admin/super/api/change',json={'revision':rev,'reason':'Disable account','changes':[{'kind':'staff','id':1,'value':{'enabled':False}}]})
 assert result.status_code==200,result.text
 with m.db() as c:
  for table in ('adm227_team_sessions','adm227_challenges','adm227_invites'):assert c.execute('SELECT COUNT(*) FROM '+table+' WHERE staff_id=1').fetchone()[0]==0

@pytest.mark.parametrize('cookie',[None,'unknown-session'])
def test_missing_team_session_is_401_not_500(panel,monkeypatch,cookie):
 _,client,_=panel;monkeypatch.setitem(admin.G,'current_user',lambda request:None)
 client.cookies.clear()
 if cookie:client.cookies.set('nowup_team227',cookie)
 assert client.get('/admin/super/api/state').status_code==401

def test_paging_reads_all_orders_once_and_items_only_for_page(panel):
 m,client,_=panel
 with m.db() as c:
  pid=c.execute('SELECT id FROM professionals LIMIT 1').fetchone()[0];now=datetime.now(timezone.utc).isoformat()
  for i in range(405):
   oid=c.execute("INSERT INTO orders(professional_id,customer_name,status,total_cents,created_at,updated_at) VALUES(?,'Audit','new',300,?,?)",(pid,now,now)).lastrowid
   c.execute("INSERT INTO order_items(order_id,product_name,quantity,unit_price_cents) VALUES(?,'Item',1,300)",(oid,))
 first=client.get('/admin/super/api/state');assert first.status_code==200,first.text
 data=first.json();orders=data['orders'];assert len(orders)==200
 cursor=data['_meta']['orderPagination255']['nextBefore']
 while cursor:
  page=client.get('/admin/super/api/orders-page',params={'before_id':cursor}).json()
  orders+=page['orders'];cursor=page['nextBefore']
 assert len(orders)==405 and len({o['id'] for o in orders})==405
 assert sum(o['total'] for o in orders)==405*300
 assert all(len(o['items'])==1 for o in orders)
 assert client.get('/admin/super/api/orders-page?limit=1000').status_code==400
 # Historical orders beyond the first page remain editable, with optimistic checks.
 rev=data['_meta']['revision'];oldest=orders[-1]
 result=client.post('/admin/super/api/change',json={'revision':rev,'reason':'Check old order','changes':[{'kind':'orders','id':oldest['id'],'value':{'courier':None},'before':{'status':'new'}}]})
 assert result.status_code==200,result.text

def test_orders_endpoint_does_not_grant_missing_permissions(panel,monkeypatch):
 m,client,_=panel;monkeypatch.setitem(admin.G,'current_user',lambda request:None)
 with m.db() as c:
  admin.put(c,'staff',1,{'id':1,'name':'Marketing','email':'m@example.invalid','enabled':True,'permissions':['marketing']})
  c.execute('INSERT INTO adm227_team_sessions VALUES(?,?,?)',(admin.tokenhash('team-only'),1,'2099'))
 client.cookies.set('nowup_team227','team-only')
 assert client.get('/admin/super/api/orders-page').json()['orders']==[]

def test_concurrent_sqlite_submissions_create_one_committed_order(tmp_path):
 from nowup_checkout229 import begin_checkout,remember_checkout
 path=tmp_path/'parallel.db'
 with sqlite3.connect(path) as c:c.executescript('CREATE TABLE orders(id INTEGER PRIMARY KEY,tracking_token TEXT);CREATE TABLE checkout_requests229(customer_id INTEGER,professional_id INTEGER,request_key TEXT,payload_hash TEXT,order_id INTEGER,created_at TEXT,PRIMARY KEY(customer_id,professional_id,request_key));')
 barrier=Barrier(2)
 def submit(i):
  c=sqlite3.connect(path,timeout=10);c.row_factory=sqlite3.Row
  try:
   barrier.wait(timeout=5);existing,key,digest=begin_checkout(c,1,2,'same-key-parallel255',{'cart':'[]'})
   if existing:return existing
   token='token-'+str(i);oid=c.execute('INSERT INTO orders(tracking_token) VALUES(?)',(token,)).lastrowid
   remember_checkout(c,1,2,key,digest,oid,datetime.now(timezone.utc).isoformat());c.commit();return token
  finally:c.close()
 with ThreadPoolExecutor(max_workers=2) as pool:tokens=list(pool.map(submit,[1,2]))
 assert tokens[0]==tokens[1]
 with sqlite3.connect(path) as c:assert c.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==1


def test_personal_pages_are_not_cacheable(checkout):
 _,client,_,_,_,_=checkout
 result=client.get('/entrar',follow_redirects=False)
 assert result.headers.get('cache-control')=='private, no-store'
 assert 'Cookie' in result.headers.get('vary','')
