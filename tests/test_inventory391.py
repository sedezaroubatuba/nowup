"""Stock invariants through real HTTP routes and transactions."""
import json,time
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
import pytest
from test_checkout247 import checkout
from test_storeapp256 import shop
from test_storeapp257 import channel

@pytest.fixture
def inventory(channel,monkeypatch):
 m,client,slug,pid,data,product,buyer=channel
 from nowup_custom192 import save_config
 from nowup_fashion385 import config
 from nowup_inventory391 import configure
 with m.db() as c:
  c.execute("UPDATE professionals SET business_type='fashion',is_demo=0,plan_active='cardapio' WHERE id=?",(pid,))
  stock={'mode':'variants','variants':[{'size':'M','color':'Preto','quantity':10},{'size':'M','color':'Branco','quantity':2}]}
  c.execute('UPDATE products SET fashion_details387=? WHERE id=?',(json.dumps({'stock':stock}),product))
  save_config(c,product,config('letters','M','Preto, Branco'));configure(c,product,stock)
  owner=dict(c.execute('SELECT u.* FROM users u JOIN professionals p ON p.user_id=u.id WHERE p.id=?',(pid,)).fetchone())
  ids=[]
  for n in range(30):ids.append(c.execute("INSERT INTO users(role,name,email,phone,password_hash,created_at) VALUES('customer',?,?,?,'unused',?)",(f'Cliente {n}',f'concurrent391-{n}@example.invalid','12988887777',m.now_iso())).lastrowid)
 def user(request):
  if request.headers.get('x-owner391'):return owner
  return dict(buyer,id=int(request.headers.get('x-user391',buyer['id'])))
 monkeypatch.setattr(m,'current_user',user)
 cart=lambda qty=2,color='Preto':json.dumps([{'id':product,'quantity':qty,'price':1,'customization':{'groups':{'fashionSize385':['M'],'fashionColor385':[color]}}}])
 return m,client,slug,pid,data,product,buyer,ids,cart


def test_30_customers_cannot_reserve_more_than_10(inventory):
 m,_,slug,pid,data,product,buyer,ids,cart=inventory
 # Do not invoke lifespan/background workers for a concurrency test.
 def reserve(n):
  client=TestClient(m.app,headers={'Origin':'http://testserver','x-user391':str(ids[n])})
  return client.post('/p/'+slug+'/menu/estoque/reservar',data={'cart_json':cart(),'basket_key':f'reservation391-{n:04d}'}).status_code
 with ThreadPoolExecutor(max_workers=12) as ex:codes=list(ex.map(reserve,range(30)))
 assert codes.count(200)==5 and codes.count(409)==25,codes
 with m.db() as c:assert c.execute("SELECT SUM(quantity) FROM fashion_holds391 WHERE state='held'").fetchone()[0]==10


def test_expiry_removal_and_independent_color(inventory,monkeypatch):
 m,c,slug,pid,data,product,buyer,ids,cart=inventory
 path='/p/'+slug+'/menu/estoque/reservar'
 assert c.post(path,data={'cart_json':cart(10),'basket_key':'reservation391-main'}).status_code==200
 other={'x-user391':str(ids[0])}
 assert c.post(path,headers=other,data={'cart_json':cart(1),'basket_key':'reservation391-other'}).status_code==409
 assert c.post(path,headers=other,data={'cart_json':cart(2,'Branco'),'basket_key':'reservation391-white'}).status_code==200
 with m.db() as db:db.execute('UPDATE fashion_holds391 SET expires_at=?',(time.time()-1,))
 assert c.post(path,headers=other,data={'cart_json':cart(10),'basket_key':'reservation391-other'}).status_code==200
 assert c.post(path,headers=other,data={'cart_json':'[]','basket_key':'reservation391-other'}).status_code==200
 assert c.post(path,data={'cart_json':cart(10),'basket_key':'reservation391-main'}).status_code==200


def test_checkout_confirm_cancel_and_retry_are_atomic(inventory):
 m,c,slug,pid,data,product,buyer,ids,cart=inventory
 path='/p/'+slug+'/menu/estoque/reservar';basket='reservation391-checkout'
 assert c.post(path,data={'cart_json':cart(),'basket_key':basket}).status_code==200
 body={**data,'cart_json':cart(),'basket_key391':basket}
 first=c.post('/p/'+slug+'/menu/whatsapp',data=body);assert first.status_code==200,first.text
 assert first.json()['total_cents']==600 and 'whatsapp_url' in first.json()
 assert c.post('/p/'+slug+'/menu/whatsapp',data=body).json()==first.json()
 with m.db() as db:
  oid=db.execute('SELECT id FROM orders').fetchone()[0]
  assert db.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==1
  assert db.execute("SELECT on_hand FROM fashion_inventory391 WHERE color='Preto'").fetchone()[0]==10
 endpoint='/painel/pedidos/'+str(oid)+'/status'
 assert c.post(endpoint,headers={'x-owner391':'1'},data={'status':'confirmed'},follow_redirects=False).status_code==303
 assert c.post(endpoint,headers={'x-owner391':'1'},data={'status':'confirmed'},follow_redirects=False).status_code==303
 with m.db() as db:assert db.execute("SELECT on_hand FROM fashion_inventory391 WHERE color='Preto'").fetchone()[0]==8
 assert c.post(endpoint,headers={'x-owner391':'1'},data={'status':'cancelled','reason':'Cliente desistiu da compra'},follow_redirects=False).status_code==303
 with m.db() as db:assert db.execute("SELECT on_hand FROM fashion_inventory391 WHERE color='Preto'").fetchone()[0]==10


def test_checkout_cannot_steal_another_customers_hold(inventory):
 m,c,slug,pid,data,product,buyer,ids,cart=inventory
 assert c.post('/p/'+slug+'/menu/estoque/reservar',data={'cart_json':cart(10),'basket_key':'reservation391-owner'}).status_code==200
 r=c.post('/p/'+slug+'/menu/whatsapp',headers={'x-user391':str(ids[0])},data={**data,'cart_json':cart(10),'basket_key391':'reservation391-owner'})
 assert r.status_code==409
 with m.db() as db:assert db.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==0
