from datetime import datetime,timedelta,timezone
from test_merchant228 import env

def test_super_admin_core_buttons(env):
 m,client,ids,pid,other=env
 with m.db() as c:
  uid=c.execute("SELECT id FROM users WHERE role='admin' LIMIT 1").fetchone()[0]
  c.execute('INSERT INTO sessions(token,user_id,expires_at) VALUES(?,?,?)',('audit-super342',uid,(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()))
 client.cookies.set('nowup_session','audit-super342')
 state=client.get('/admin/super/api/state');assert state.status_code==200,state.text
 snapshot=state.json();assert {x['id'] for x in snapshot['plans']}=={'cardapio','ambos','completo'}
 def change(kind,oid,value):
  current=client.get('/admin/super/api/state').json()
  return client.post('/admin/super/api/change',json={'revision':current['_meta']['revision'],'reason':'Auditoria isolada de botões do administrador','changes':[{'kind':kind,'id':oid,'value':value}]},headers={'X-Nowup-Admin':'227'})
 assert change('stores',pid,{'paused':True}).status_code==200
 assert change('stores',pid,{'paused':False}).status_code==200
 assert change('stores',pid,{'plan':'cardapio'}).status_code==200
 assert change('stores',pid,{'plan':'ambos'}).status_code==200
 assert change('orders',ids['Ana <script>alert(1)</script>'],{'status':'confirmed'}).status_code==200
 assert change('orders',ids['Ana <script>alert(1)</script>'],{'status':'preparing'}).status_code==200
 assert change('orders',ids['Ana <script>alert(1)</script>'],{'status':'ready'}).status_code==200
 assert client.get('/admin/super/api/orders-page').status_code==200
 assert client.get('/admin/cms').status_code==200


def test_cms_rejects_customer_and_anonymous(env):
 from fastapi.testclient import TestClient
 m, *_ = env
 anonymous=TestClient(m.app)
 assert anonymous.get('/admin/cms').status_code == 403
 with m.db() as c:
  user=c.execute("SELECT id FROM users WHERE role='customer' LIMIT 1").fetchone()
  if not user:
   uid=c.execute("INSERT INTO users(role,name,email,password_hash,created_at) VALUES('customer','Customer','cms344@example.invalid','unused',?)",(datetime.now(timezone.utc).isoformat(),)).lastrowid
  else:uid=user['id']
  c.execute('INSERT INTO sessions(token,user_id,expires_at) VALUES(?,?,?)',('cms-customer344',uid,(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()))
 anonymous.cookies.set('nowup_session','cms-customer344')
 assert anonymous.get('/admin/cms').status_code==403
