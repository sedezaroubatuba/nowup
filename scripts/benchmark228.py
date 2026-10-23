"""Disposable local benchmark; never opens the configured production database."""
import json,os,secrets,sys,tempfile,time,statistics
from pathlib import Path
from datetime import datetime,timedelta,timezone
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

def run():
 with tempfile.TemporaryDirectory(prefix='nowup-bench228-') as directory:
  os.environ.update(NOWUP_DB=directory+'/test.db',NOWUP_UPLOAD_DIR=directory+'/uploads',NOWUP_ADMIN_EMAIL='benchmark@test.invalid',NOWUP_ADMIN_PASSWORD='isolated-benchmark-password',NOWUP_ADMIN_SECRET=secrets.token_hex(32),NOWUP_JWT_SECRET=secrets.token_hex(32),NOWUP_BILLING_WORKER='0')
  import app as m
  from fastapi.testclient import TestClient
  for callback in m.app.router.on_startup:
   if callback.__name__!='start':callback()
  token=secrets.token_hex(32);now=m.now_iso();expiry=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat();stores=[]
  with m.db() as c:
   admin=c.execute("SELECT id FROM users WHERE role='admin'").fetchone()[0];c.execute('INSERT INTO sessions VALUES(?,?,?)',(token,admin,expiry))
   for i in range(500):
    uid=c.execute("INSERT INTO users(role,name,email,password_hash,created_at) VALUES('professional',?,?,'invalid',?)",('Benchmark '+str(i),str(i)+'@benchmark.invalid',now)).lastrowid
    stores.append(c.execute("INSERT INTO professionals(user_id,slug,display_name,created_at,is_demo,admission_status,subscription_status,kyc_status) VALUES(?,?,?,?,0,'approved','active','approved')",(uid,'benchmark-'+str(i),'Benchmark '+str(i),now)).lastrowid)
   c.executemany("INSERT INTO orders(professional_id,customer_name,status,total_cents,created_at,updated_at,delivery_neighborhood) VALUES(?,'Bench','completed',3000,?,?,'Centro')",[(stores[i%500],'2026-10-22T21:30:00+00:00',now) for i in range(30000)])
   c.commit()
  client=TestClient(m.app,base_url='https://testserver');client.cookies.set('nowup_session',token)
  url='/admin/super/api/metrics?from=2026-10-22&to=2026-10-22'
  def request(_):
   t=time.perf_counter();r=client.get(url);return {'ms':round((time.perf_counter()-t)*1000,2),'status':r.status_code,'bytes':len(r.content)}
  m.nowup_data228.invalidate();cold=request(0)
  warm=request(0)
  m.nowup_data228.invalidate()
  with ThreadPoolExecutor(max_workers=10) as pool:concurrent=list(pool.map(request,range(10)))
  p95=sorted(x['ms'] for x in concurrent)[-1]
  state=client.get('/admin/super/api/state');orders=client.get('/admin/super/api/orders?from=2026-10-22&to=2026-10-22')
  result={'stores':500,'orders':30000,'metrics_cold':cold,'metrics_warm':warm,'concurrent_requests':10,'concurrent_p95_ms_nearest_rank':p95,'statuses':[r['status'] for r in concurrent],'state_bytes':len(state.content),'state_orders':len(state.json()['orders']),'orders_page_size':len(orders.json()['items']),'orders_total':orders.json()['total'],'metrics':client.get(url).json()}
  result['acceptance']={'metrics_under_100ms':cold['ms']<100,'metrics_under_100kb':cold['bytes']<100000,'no_500_in_10_requests':all(x['status']==200 for x in concurrent),'concurrent_p95_under_300ms':p95<300}
  print(json.dumps(result,ensure_ascii=False,indent=2))
  m.nowup_runtime228.stop_worker()
if __name__=='__main__':run()
