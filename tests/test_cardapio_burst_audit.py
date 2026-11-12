"""Audit burst against disposable local DB; never sends WhatsApp messages or email."""
import ast,json,secrets,time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
from pathlib import Path
from statistics import median
from fastapi.testclient import TestClient
from bs4 import BeautifulSoup
from test_checkout247 import checkout
from test_storeapp256 import shop
from test_storeapp257 import channel
from test_pix import KEY


def test_cardapio_burst_and_ten_links_share_owner_session(channel,monkeypatch):
    m,_,slug,pid,payload,product,_=channel
    tree=ast.parse(Path(m.__file__).read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='current_user')
    scope={};exec(compile(ast.Module(body=[node],type_ignores=[]),m.__file__,'exec'),m.__dict__,scope)
    monkeypatch.setattr(m,'current_user',scope['current_user'])
    monkeypatch.setattr(m,'send_email',lambda *a,**k:False)
    customers=[];stamp=m.now_iso();expires=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
    with m.db() as c:
        m.nowup_notinha401.initialize(c)
        c.execute("UPDATE professionals SET plan_active='cardapio',whatsapp='12999999999',pix_key=?,pix_key_type='random',pix_receiver_name='Loja auditoria',pix_receiver_city='Ubatuba' WHERE id=?",(KEY,pid))
        owner=c.execute('SELECT user_id FROM professionals WHERE id=?',(pid,)).fetchone()[0]
        c.execute('INSERT INTO sessions(token,user_id,expires_at) VALUES(?,?,?)',('audit-owner-session',owner,expires))
        for i in range(161):
            email=f'burst-audit-{i}@example.invalid'
            uid=c.execute("INSERT INTO users(role,name,email,phone,password_hash,email_verified,created_at,customer_store345,customer_email345) VALUES('customer',?,?,?,'unused',1,?,?,?)",(f'Cliente de teste {i}',email,'12988887777',stamp,pid,email)).lastrowid
            token='audit-customer-'+str(i)
            c.execute('INSERT INTO sessions(token,user_id,expires_at,store_id345) VALUES(?,?,?,?)',(token,uid,expires,pid))
            customers.append((uid,token))
    endpoint='/p/'+slug+'/menu/whatsapp'
    def order(i):
        client=TestClient(m.app,headers={'Origin':'http://testserver'},follow_redirects=False)
        client.cookies.set('nowup_loja345_'+str(pid),customers[i][1],path='/p/'+slug)
        data={**payload,'payment_method':['pix','cash','credit','debit'][i%4],'request_key':f'burst-audit-request-{i:05d}'}
        start=time.perf_counter()
        try:
            response=client.post(endpoint,data=data)
            result=response.json();elapsed=time.perf_counter()-start
            return {'i':i,'status':response.status_code,'time':elapsed,'result':result,'data':data}
        finally:client.close()
    report={'engine':'isolated SQLite; not production PostgreSQL or WhatsApp delivery','scenarios':[]}
    results=[]
    for label,ids in [('10 simultaneous',range(10)),('150 orders, concurrency 10',range(10,160))]:
        start=time.perf_counter()
        with ThreadPoolExecutor(max_workers=10) as pool:batch=list(pool.map(order,ids))
        times=sorted(x['time'] for x in batch)
        report['scenarios'].append({'scenario':label,'count':len(batch),'success':sum(x['status']==200 for x in batch),'seconds':round(time.perf_counter()-start,3),'median_seconds':round(median(times),3),'p95_seconds':round(times[int((len(times)-1)*.95)],3),'statuses':[x['status'] for x in batch if x['status']!=200]})
        results+=batch
    Path('/tmp/nowup-burst-audit.json').write_text(json.dumps(report,indent=2))
    assert all(x['status']==200 for x in results),report
    assert len({x['result']['order_code'] for x in results})==160
    assert all(x['result']['total_cents']==300 and 'pix' not in x['result'] for x in results)
    with m.db() as c:
        assert c.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==160
        assert c.execute("SELECT COUNT(*) FROM orders WHERE order_origin='external' AND status='new'").fetchone()[0]==160
    # Ten merchant tabs, a single persisted owner session, full order controls.
    def merchant_open(entry):
        client=TestClient(m.app,headers={'Origin':'http://testserver'},follow_redirects=False);client.cookies.set('nowup_session','audit-owner-session')
        path=entry['result']['merchant_url'].replace('http://testserver','')
        response=client.get(path)
        soup=BeautifulSoup(response.text,'html.parser')
        ok=response.status_code==200 and bool(soup.select_one('form[action$="/status"] button[value="confirmed"]'))
        client.close();return ok
    with ThreadPoolExecutor(max_workers=10) as pool:assert all(pool.map(merchant_open,results[:10]))
    report['merchant_links_open_without_login']=10
    merchant=TestClient(m.app,headers={'Origin':'http://testserver'},follow_redirects=False);merchant.cookies.set('nowup_session','audit-owner-session')
    statuses=[]
    for entry in results[:10]:
        token=entry['result']['merchant_url'].split('/pedido/')[1].split('?')[0]
        with m.db() as c:oid=c.execute('SELECT id FROM orders WHERE tracking_token=?',(token,)).fetchone()[0]
        for status in ['confirmed','preparing','ready','out_for_delivery','completed']:
            r=merchant.post(f'/painel/pedidos/{oid}/status',data={'status':status},headers={'Accept':'application/json'});assert r.status_code==200,(status,r.status_code,r.text)
            if status=='confirmed' and entry['data']['payment_method']=='pix':
                page=merchant.get('/pedido/'+token)
                assert BeautifulSoup(page.text,'html.parser').select_one('[data-pix-payment]')
                assert merchant.post(f'/painel/pedidos/{oid}/conferir-pix').status_code==303
        statuses.append(oid)
    # Repeat checkout: same key gives same order, no duplicate.
    repeated=order(15);assert repeated['status']==200 and repeated['result']['order_code']==results[15]['result']['order_code']
    # Anti-spam: sixth unique order for one customer must be blocked.
    spam=TestClient(m.app,headers={'Origin':'http://testserver'},follow_redirects=False);spam.cookies.set('nowup_loja345_'+str(pid),customers[160][1],path='/p/'+slug)
    codes=[spam.post(endpoint,data={**payload,'request_key':f'spam-audit-request-{i:05d}'}).status_code for i in range(6)]
    assert codes==[200]*5+[429],codes
    report.update(merchant_orders_completed=len(statuses),duplicate_checkout='no duplicate',anti_spam=codes)
    Path('/tmp/nowup-burst-audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
