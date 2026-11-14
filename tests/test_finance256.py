"""Financial and inventory regressions use temporary SQLite databases only."""
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from urllib.parse import urlparse, parse_qs
import pytest
from fastapi.testclient import TestClient
from test_checkout247 import checkout
import nowup_finance256 as finance

@pytest.fixture
def env(checkout, monkeypatch):
    m,client,url,data,product,customer=checkout
    m.nowup_sales107.initialize()
    with m.db() as c:
        finance.initialize(c)
        m.nowup_review127.initialize(c)
        p=dict(c.execute('SELECT p.* FROM professionals p JOIN products x ON x.professional_id=p.id WHERE x.id=?',(product,)).fetchone())
    actor={'id':p['user_id'],'role':'professional'}
    monkeypatch.setattr(m,'require_user',lambda request,role:actor if role=='professional' else customer)
    monkeypatch.setattr(m.nowup_sales107,'_auth',m.require_user)
    return m,client,url,data,product,customer,p

def open_cash(e,initial='100',token='open-session-256-first'):
    m,c,*_=e
    r=c.post('/painel/caixa/abrir',data={'initial':initial,'token':token},follow_redirects=False)
    assert r.status_code==303,r.text
    with m.db() as db:return db.execute('SELECT MAX(id) FROM cash_sessions256').fetchone()[0]

def order(e,method='pix',token='order-256-unique-first'):
    m,c,url,data,*_=e
    r=c.post(url,data={**data,'payment_method':method,'request_key':token},follow_redirects=False)
    assert r.status_code==303,r.text
    with m.db() as db:return db.execute('SELECT MAX(id) FROM orders').fetchone()[0]

def change(e,oid,status):
    return e[1].post(f'/painel/pedidos/{oid}/status',data={'status':status,'reason':'teste isolado'},follow_redirects=False)

def complete(e,oid):
    for status in ('confirmed','preparing','ready','completed'):
        r=change(e,oid,status);assert r.status_code==303,r.text


def test_cash_reconciles_and_freezes(env):
    m,c,*_=env;sid=open_cash(env)
    with m.db() as db:db.execute('UPDATE products SET price_cents=5000 WHERE id=?',(env[4],))
    oid=order(env,'cash');complete(env,oid)
    with m.db() as db:db.execute('UPDATE products SET price_cents=8000 WHERE id=?',(env[4],))
    complete(env,order(env,'pix','order-256-second-pix'))
    with m.db() as db:db.execute('UPDATE products SET price_cents=12000 WHERE id=?',(env[4],))
    complete(env,order(env,'credit','order-256-third-card'))
    assert change(env,oid,'completed').status_code==303
    for kind,value in [('supply','20'),('withdrawal','30')]:
        payload={'kind':kind,'value':value,'reason':'conferência','token':'move-256-'+kind+'-unique'}
        for _ in range(2):assert c.post(f'/painel/caixa/{sid}/movimento',data=payload,follow_redirects=False).status_code==303
    with m.db() as db:
        s=finance.session(db,env[6]['id'],sid);r=finance.summary(db,s)
        assert r['sales_cents']==25000 and r['sales_count']==3
        assert r['expected_cents']==14000
        assert r['payments']=={'cash':5000,'pix':8000,'credit':12000,'debit':0}
    assert c.post(f'/painel/caixa/{sid}/fechar',data={'counted':'140'},follow_redirects=False).status_code==303
    with m.db() as db:
        s=finance.session(db,env[6]['id'],sid);snapshot=s['snapshot']
        with pytest.raises(sqlite3.IntegrityError):db.execute('UPDATE orders SET total_cents=1 WHERE id=?',(oid,))
        assert finance.summary(db,s)['sales_cents']==25000
    assert c.get(f'/painel/caixa?caixa={sid}').status_code==200
    assert c.post(f'/painel/caixa/{sid}/fechar',data={'counted':'140'},follow_redirects=False).status_code==409
    with m.db() as db:assert db.execute('SELECT snapshot FROM cash_sessions256 WHERE id=?',(sid,)).fetchone()[0]==snapshot
    open_cash(env,'140','open-session-256-second')


def test_cancel_pending_and_unknown_payment(env):
    m,c,*_=env;sid=open_cash(env);oid=order(env)
    assert c.post(f'/painel/caixa/{sid}/fechar',data={'counted':'100'},follow_redirects=False).status_code==409
    assert change(env,oid,'cancelled').status_code==303
    with m.db() as db:
        r=finance.summary(db,finance.session(db,env[6]['id'],sid))
        assert not r['pending'] and r['sales_cents']==0 and r['expected_cents']==10000
    oid=order(env,'on_delivery','order-256-unknown-payment')
    for status in ('confirmed','preparing','ready'):assert change(env,oid,status).status_code==303
    assert change(env,oid,'completed').status_code==409


def test_open_idempotent_and_cross_tenant(env):
    m,c,*_=env;sid=open_cash(env)
    assert open_cash(env)==sid
    assert c.post('/painel/caixa/abrir',data={'initial':'10','token':'open-session-256-other'},follow_redirects=False).status_code==409
    with m.db() as db:other=db.execute('SELECT id FROM professionals WHERE id!=? LIMIT 1',(env[6]['id'],)).fetchone()[0]
    with m.db() as db:
        db.execute('INSERT INTO cash_sessions256(professional_id,opened_by,opened_at,opening_cents,open_token) VALUES(?,?,?,?,?)',(other,1,finance.stamp(),0,'other-store-open-token'))
        foreign=db.execute('SELECT MAX(id) FROM cash_sessions256').fetchone()[0]
    assert c.get('/painel/caixa?caixa='+str(foreign)).status_code==404
    assert c.post(f'/painel/caixa/{foreign}/fechar',data={'counted':'0'},follow_redirects=False).status_code==404


def test_withdrawal_and_difference_checks(env):
    sid=open_cash(env);c=env[1]
    assert c.post(f'/painel/caixa/{sid}/movimento',data={'kind':'withdrawal','value':'101','reason':'teste','token':'movement-256-too-large'},follow_redirects=False).status_code==400
    assert c.post(f'/painel/caixa/{sid}/fechar',data={'counted':'99'},follow_redirects=False).status_code==400
    assert c.post(f'/painel/caixa/{sid}/fechar',data={'counted':'99','reason':'Conferência: falta R$ 1'},follow_redirects=False).status_code==303


def test_zero_order_is_atomic(env):
    m,c,url,data,pid,*_=env
    with m.db() as db:db.execute('UPDATE products SET price_cents=0 WHERE id=?',(pid,))
    assert c.post(url,data=data,follow_redirects=False).status_code==400
    with m.db() as db:
        assert db.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==0
        assert db.execute('SELECT COUNT(*) FROM checkout_requests229').fetchone()[0]==0


def test_whatsapp_status_and_address(env):
    m,c,*_=env;oid=order(env)
    with m.db() as db:
        db.execute("UPDATE orders SET address='Rua João, 10',neighborhood='Centro',address_reference='Portão azul',fulfillment_type='delivery',notes='Sem gelo' WHERE id=?",(oid,))
    r=c.get(f'/painel/pedidos/{oid}/whatsapp',follow_redirects=False)
    assert r.status_code==303
    link=urlparse(r.headers['location']);assert link.netloc=='wa.me' and link.path=='/5512999999999'
    text=parse_qs(link.query)['text'][0]
    assert all(t in text for t in ['Rua João, 10','Centro','Portão azul','Sem gelo','Audit','NU-','3.00'])
    assert change(env,oid,'confirmed').status_code==303
    text=parse_qs(urlparse(c.get(f'/painel/pedidos/{oid}/whatsapp',follow_redirects=False).headers['location']).query)['text'][0]
    assert 'Pedido confirmado' in text
    with m.db() as db:db.execute("UPDATE orders SET customer_phone='bad' WHERE id=?",(oid,))
    assert c.get(f'/painel/pedidos/{oid}/whatsapp',follow_redirects=False).status_code==400


def test_delivery_change_requires_approval(env):
    m,c,*_=env;oid=order(env)
    with m.db() as db:db.execute('UPDATE professionals SET allows_delivery=1,delivery_fee_cents=800 WHERE id=?',(env[6]['id'],))
    payload={'customer_name':'Audit','customer_phone':'12999999999','fulfillment_type':'delivery','payment_method':'pix','address':'Rua A 1','neighborhood':'Centro'}
    r=c.post(f'/painel/pedidos/{oid}/editar',data=payload,follow_redirects=False);assert r.status_code==303,r.text
    with m.db() as db:
        o=db.execute('SELECT * FROM orders WHERE id=?',(oid,)).fetchone()
        assert o['total_cents']==300 and o['status']=='awaiting_approval'
        rev=db.execute('SELECT * FROM order_revisions WHERE order_id=?',(oid,)).fetchone()
    r=c.post(f"/pedido/{o['tracking_token']}/revisao/{rev['id']}",data={'decision':'accept'},follow_redirects=False);assert r.status_code==303,r.text
    with m.db() as db:
        o=db.execute('SELECT * FROM orders WHERE id=?',(oid,)).fetchone()
        assert o['total_cents']==1100 and o['delivery_fee_cents']==800 and o['status']=='revision_approved'
    r=c.post(f'/painel/pedidos/{oid}/editar',data={**payload,'fulfillment_type':'pickup'},follow_redirects=False);assert r.status_code==303,r.text
    with m.db() as db:rev=db.execute('SELECT * FROM order_revisions ORDER BY id DESC LIMIT 1').fetchone()
    assert c.post(f"/pedido/{o['tracking_token']}/revisao/{rev['id']}",data={'decision':'accept'},follow_redirects=False).status_code==303
    with m.db() as db:
        o=db.execute('SELECT * FROM orders WHERE id=?',(oid,)).fetchone()
        assert o['total_cents']==300 and o['delivery_fee_cents']==0 and o['address']==''


def test_stock_reserve_cancel_retry_and_isolation(env):
    m,c,url,data,pid,*_=env
    assert c.post('/painel/estoque/'+str(pid),data={'quantity':'1','previous':''},follow_redirects=False).status_code==303
    oid=order(env)
    with m.db() as db:assert db.execute('SELECT stock256 FROM products WHERE id=?',(pid,)).fetchone()[0]==0
    assert c.post(url,data={**data,'request_key':'stock-256-second-order'},follow_redirects=False).status_code==409
    assert c.post(url,data={**data,'request_key':'order-256-unique-first'},follow_redirects=False).status_code==303
    assert c.post('/painel/estoque/'+str(pid),data={'quantity':'5','previous':'0'},follow_redirects=False).status_code==409
    assert change(env,oid,'cancelled').status_code==303
    assert change(env,oid,'cancelled').status_code==303
    with m.db() as db:assert db.execute('SELECT stock256 FROM products WHERE id=?',(pid,)).fetchone()[0]==1


def test_status_skips_and_direct_database_bypass(env):
    m,c,*_=env;oid=order(env)
    assert change(env,oid,'confirmed').status_code==303
    assert change(env,oid,'completed').status_code==409
    with m.db() as db:
        with pytest.raises(sqlite3.IntegrityError):db.execute("UPDATE orders SET status='completed' WHERE id=?",(oid,))


def test_manual_payments_refund_and_payment_id_reuse(env):
    m,c,*_=env;sid=open_cash(env)
    assert c.post('/painel/vendas-manuais/abrir',data={'label':'Comanda QA','channel':'presential','token':'manual-256-create-first'},follow_redirects=False).status_code==303
    with m.db() as db:mid=db.execute('SELECT MAX(id) FROM manual_sales107').fetchone()[0]
    def mutate(action,version,**kw):return c.post(f'/painel/vendas-manuais/{mid}/alterar',data={'action':action,'version':version,**kw},follow_redirects=False)
    assert mutate('item',0,product_id=env[4],quantity=2).status_code==303
    assert mutate('payment',1,method='cash',amount='3').status_code==303
    with m.db() as db:pay=db.execute('SELECT MAX(id) FROM manual_payments107').fetchone()[0]
    assert mutate('remove_payment',2,payment_id=pay,reason='Troca de pagamento').status_code==303
    assert mutate('payment',3,method='pix',amount='3').status_code==303
    assert mutate('cancel',4,reason='Cliente desistiu',refund='1').status_code==303
    with m.db() as db:
        r=finance.summary(db,finance.session(db,env[6]['id'],sid))
        assert r['sales_cents']==0 and r['expected_cents']==10000 and r['payments']['pix']==0


def test_migration_is_idempotent_and_legacy_not_imported(env):
    m,c,*_=env;oid=order(env);complete(env,oid)
    sid=open_cash(env)
    with m.db() as db:
        finance.initialize(db);finance.initialize(db)
        r=finance.summary(db,finance.session(db,env[6]['id'],sid))
        assert r['sales_count']==0 and r['sales_cents']==0
    assert c.get('/painel/estoque').status_code==200
    assert c.get('/painel/caixa').status_code==200


def test_concurrent_open_and_last_unit(env):
    m,c,url,data,pid,*_=env
    barrier=Barrier(2)
    def opening(i):
        client=TestClient(m.app,headers={'Origin':'http://testserver'})
        barrier.wait(timeout=10)
        return client.post('/painel/caixa/abrir',data={'initial':'0','token':'parallel-open-256-'+str(i)},follow_redirects=False).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:assert sorted(pool.map(opening,range(2)))==[303,409]
    assert c.post('/painel/estoque/'+str(pid),data={'quantity':'1','previous':''},follow_redirects=False).status_code==303
    barrier=Barrier(2)
    def buying(i):
        client=TestClient(m.app,headers={'Origin':'http://testserver'})
        barrier.wait(timeout=10)
        return client.post(url,data={**data,'request_key':'parallel-stock-256-'+str(i)},follow_redirects=False).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:assert sorted(pool.map(buying,range(2)))==[303,409]
    with m.db() as db:
        assert db.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==1
        assert db.execute('SELECT stock256 FROM products WHERE id=?',(pid,)).fetchone()[0]==0


def test_stock_revision_failure_rolls_back(env):
    m,c,*_=env;pid=env[4]
    assert c.post('/painel/estoque/'+str(pid),data={'quantity':'2','previous':''},follow_redirects=False).status_code==303
    oid=order(env)
    assert change(env,oid,'reviewing').status_code==303
    with m.db() as db:item=db.execute('SELECT id FROM order_items WHERE order_id=?',(oid,)).fetchone()[0]
    r=c.post(f'/painel/pedidos/{oid}/revisao',data={'keep':str(item),'qty_'+str(item):'3'},follow_redirects=False);assert r.status_code==303,r.text
    with m.db() as db:
        o=db.execute('SELECT * FROM orders WHERE id=?',(oid,)).fetchone();rev=db.execute('SELECT MAX(id) FROM order_revisions').fetchone()[0]
    assert c.post(f"/pedido/{o['tracking_token']}/revisao/{rev}",data={'decision':'accept'},follow_redirects=False).status_code==409
    with m.db() as db:
        assert db.execute('SELECT quantity FROM order_items WHERE id=?',(item,)).fetchone()[0]==1
        assert db.execute('SELECT stock256 FROM products WHERE id=?',(pid,)).fetchone()[0]==1
        assert db.execute('SELECT status FROM orders WHERE id=?',(oid,)).fetchone()[0]=='awaiting_approval'


def test_500_orders_50_concurrent_reconcile(env,monkeypatch):
    """Accelerated LOCAL load, not a two-hour production capacity test."""
    import time
    m,c,url,data,pid,_,p=env
    sid=open_cash(env,'0')
    now=finance.stamp()
    with m.db() as db:
        customers=[db.execute("INSERT INTO users(role,name,email,password_hash,created_at) VALUES('customer',?,?,?,?)",('QA '+str(i),f'load256-{i}@example.invalid','unused',now)).lastrowid for i in range(50)]
    monkeypatch.setattr(m,'current_user',lambda request:{'id':int(request.headers.get('x-test-customer',customers[0])),'role':'customer'})
    latencies=[];expected={};methods=['cash','pix','credit','debit'];started=time.perf_counter()
    def submit(i):
        client=TestClient(m.app,headers={'Origin':'http://testserver','X-Test-Customer':str(customers[i%50])})
        key='local-load-256-'+str(i).zfill(5)
        payload={**data,'request_key':key,'payment_method':methods[i%4]}
        t=time.perf_counter();r=client.post(url,data=payload,follow_redirects=False);elapsed=time.perf_counter()-t
        assert r.status_code==303,r.text
        # Lost-response retry must return the same order without duplicating it.
        if i%25==0:
            retry=client.post(url,data=payload,follow_redirects=False)
            assert retry.headers['location']==r.headers['location']
        return i,key,elapsed
    with ThreadPoolExecutor(max_workers=50) as pool:
        for i,key,elapsed in pool.map(submit,range(500)):
            latencies.append(elapsed);expected[key]=customers[i%50]
    with m.db() as db:
        rows=db.execute('SELECT o.*,r.request_key FROM orders o JOIN checkout_requests229 r ON r.order_id=o.id').fetchall()
        assert len(rows)==500 and len({r['id'] for r in rows})==500
        assert all(expected[r['request_key']]==r['customer_id'] for r in rows)
        assert sum(r['total_cents'] for r in rows)==150000
    status_times=[]
    def finish(pair):
        i,row=pair;client=TestClient(m.app,headers={'Origin':'http://testserver'})
        states=['cancelled'] if i%5==0 else ['confirmed','preparing','ready','completed']
        for state in states:
            t=time.perf_counter();r=client.post(f"/painel/pedidos/{row['id']}/status",data={'status':state,'reason':'Carga local'},follow_redirects=False);elapsed=time.perf_counter()-t
            assert r.status_code==303,r.text
            status_times.append(elapsed)
    with ThreadPoolExecutor(max_workers=50) as pool:list(pool.map(finish,enumerate(rows)))
    with m.db() as db:
        report=finance.summary(db,finance.session(db,p['id'],sid))
        assert report['sales_count']==400 and report['sales_cents']==120000 and not report['pending']
        actual={r['payment_method']:r['cents'] for r in db.execute("SELECT payment_method,SUM(total_cents) cents FROM orders WHERE status='completed' GROUP BY payment_method")}
        assert all(report['payments'][method]==actual.get(method,0) for method in methods)
        assert report['expected_cents']==report['payments']['cash']
    assert c.post(f'/painel/caixa/{sid}/fechar',data={'counted':str(report['expected_cents']/100)},follow_redirects=False).status_code==303
    def metrics(values):
        values=sorted(values)
        return {'p50':round(values[int((len(values)-1)*.50)],4),'p95':round(values[int((len(values)-1)*.95)],4),'p99':round(values[int((len(values)-1)*.99)],4),'max':round(max(values),4)}
    print('\nLOCAL_LOAD_256 '+json.dumps({'orders':500,'workers':50,'delivered':400,'cancelled':100,'elapsed_seconds':round(time.perf_counter()-started,2),'create_seconds':metrics(latencies),'status_seconds':metrics(status_times),'sales_cents':report['sales_cents'],'payments_cents':report['payments']}))


def test_refund_preserves_closed_snapshot(env):
    m,c,*_=env;first=open_cash(env,'0');oid=order(env,'pix');complete(env,oid)
    assert c.post(f'/painel/caixa/{first}/fechar',data={'counted':'0'},follow_redirects=False).status_code==303
    with m.db() as db:
        original=db.execute('SELECT snapshot FROM cash_sessions256 WHERE id=?',(first,)).fetchone()[0]
        receipt=db.execute('SELECT id FROM cash_entries256 WHERE session_id=?',(first,)).fetchone()[0]
    second=open_cash(env,'0','open-session-refund-256')
    payload={'receipt_id':receipt,'value':'2','reason':'Devolução parcial','token':'refund-256-original-receipt'}
    for _ in range(2):assert c.post(f'/painel/caixa/{second}/devolver',data=payload,follow_redirects=False).status_code==303
    assert c.post(f'/painel/caixa/{second}/devolver',data={**payload,'value':'2','token':'refund-256-another-token'},follow_redirects=False).status_code==400
    with m.db() as db:
        assert db.execute('SELECT snapshot FROM cash_sessions256 WHERE id=?',(first,)).fetchone()[0]==original
        report=finance.summary(db,finance.session(db,env[6]['id'],second))
        assert report['payments']['pix']==-200 and report['sales_cents']==0 and report['expected_cents']==0


def test_access_and_cross_origin(checkout,monkeypatch):
    m,c,*_=checkout;m.nowup_sales107.initialize()
    with m.db() as db:finance.initialize(db)
    monkeypatch.setattr(m,'current_user',lambda request:None)
    assert c.get('/painel/caixa').status_code==401
    assert c.get('/painel/estoque').status_code==401
    assert c.post('/painel/caixa/abrir',data={'initial':'0','token':'access-denied-256-token'},follow_redirects=False).status_code==401
    assert c.post('/painel/caixa/abrir',data={'initial':'0','token':'access-denied-256-token'},headers={'Origin':'https://evil.invalid'},follow_redirects=False).status_code==403


def test_zero_stock_public_template_disables_buying(env):
    m,c,*_=env
    assert c.post('/painel/estoque/'+str(env[4]),data={'quantity':'0','previous':''},follow_redirects=False).status_code==303
    response=c.get('/p/'+env[6]['slug']+'/menu')
    assert response.status_code==200
    import re
    article=re.search(r'<article[^>]*data-product[^>]*data-id="'+str(env[4])+r'"[^>]*>(.*?)</article>',response.text,re.S)
    assert article and re.search(r'<button[^>]*data-add[^>]*disabled',article.group(1))
