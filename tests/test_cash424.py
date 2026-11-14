"""Cash sessions use synthetic fixtures and never the production DSN."""
import json,secrets,sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from fastapi.testclient import TestClient
import pytest
from test_checkout247 import checkout
import nowup_cash424 as cash

@pytest.fixture
def env(checkout,monkeypatch):
    m,c,url,data,pid,buyer=checkout
    m.nowup_sales107.initialize()
    with m.db() as db:
        cash.initialize(db);m.nowup_review127.initialize(db)
        p=dict(db.execute('SELECT p.* FROM professionals p JOIN products x ON x.professional_id=p.id WHERE x.id=?',(pid,)).fetchone())
    owner={'id':p['user_id'],'role':'professional'}
    original=m.current_user
    monkeypatch.setattr(m,'current_user',lambda request:buyer if request.url.path.endswith('/menu/pedido') or '/revisao/' in request.url.path else owner)
    return m,c,url,data,pid,buyer,p

def open_cash(e,initial='100',token='cash424-first-token'):
    r=e[1].post('/painel/caixa/abrir',data={'initial':initial,'token':token},follow_redirects=False)
    assert r.status_code==303,r.text
    with e[0].db() as db:return db.execute('SELECT MAX(id) FROM cash_sessions424').fetchone()[0]

def order(e,method='cash'):
    m,c,url,data,*_=e
    r=c.post(url,data={**data,'payment_method':method,'request_key':'cash424-'+secrets.token_hex(12)},follow_redirects=False)
    assert r.status_code==303,r.text
    with m.db() as db:return db.execute('SELECT * FROM orders ORDER BY id DESC LIMIT 1').fetchone()

def complete(e,o):
    c=e[1];base='/painel/pedidos/'+str(o['id'])
    if o['payment_method']=='pix':assert c.post(base+'/conferir-pix',headers={'Accept':'application/json'}).status_code==200
    for state in ('confirmed','preparing','ready','completed'):
        r=c.post(base+'/status',data={'status':state},headers={'Accept':'application/json'});assert r.status_code==200,r.text


def test_cash_math_duplicate_movements_and_freeze(env):
    m,c,*_=env;sid=open_cash(env)
    for price,method in [(5000,'cash'),(8000,'pix'),(12000,'credit')]:
        with m.db() as db:db.execute('UPDATE products SET price_cents=? WHERE id=?',(price,env[4]))
        complete(env,order(env,method))
    for kind,value in [('supply','20'),('withdrawal','30')]:
        data={'kind':kind,'value':value,'reason':'QA','token':'cash424-move-'+kind}
        for _ in range(2):assert c.post(f'/painel/caixa/{sid}/movimento',data=data,follow_redirects=False).status_code==303
    with m.db() as db:
        s=dict(db.execute('SELECT * FROM cash_sessions424 WHERE id=?',(sid,)).fetchone());report=cash.summary(db,s)
        assert report['sales_cents']==25000 and report['expected_cents']==14000 and report['sales_count']==3
    assert c.post(f'/painel/caixa/{sid}/fechar',data={'counted':'140'},follow_redirects=False).status_code==303
    with m.db() as db:
        s=dict(db.execute('SELECT * FROM cash_sessions424 WHERE id=?',(sid,)).fetchone());snap=s['snapshot']
        assert cash.summary(db,s)['expected_cents']==14000
    assert c.post(f'/painel/caixa/{sid}/fechar',data={'counted':'140'},follow_redirects=False).status_code==409
    assert c.get('/painel/caixa').status_code==200
    second=open_cash(env,'140','cash424-second-session')
    with m.db() as db:assert cash.summary(db,dict(db.execute('SELECT * FROM cash_sessions424 WHERE id=?',(second,)).fetchone()))['sales_cents']==0


def test_pending_cancelled_and_zero(env):
    m,c,*_=env;sid=open_cash(env);o=order(env)
    assert c.post(f'/painel/caixa/{sid}/fechar',data={'counted':'100'},follow_redirects=False).status_code==409
    assert c.post(f"/painel/pedidos/{o['id']}/status",data={'status':'cancelled','reason':'Teste'},follow_redirects=False).status_code==303
    with m.db() as db:
        s=dict(db.execute('SELECT * FROM cash_sessions424 WHERE id=?',(sid,)).fetchone());assert cash.summary(db,s)['sales_cents']==0
        db.execute('UPDATE products SET price_cents=0 WHERE id=?',(env[4],))
    assert c.post(env[2],data=env[3],follow_redirects=False).status_code==409
    assert c.post(f'/painel/caixa/{sid}/fechar',data={'counted':'100'},follow_redirects=False).status_code==303


def test_manual_ledger_is_frozen_after_cash_close(env):
    m,c,*_=env;sid=open_cash(env,'0')
    assert c.post('/painel/vendas-manuais/abrir',data={'label':'QA','channel':'presential','token':'cash424-manual-account'},follow_redirects=False).status_code==303
    with m.db() as db:mid=db.execute('SELECT MAX(id) FROM manual_sales107').fetchone()[0]
    def mutate(action,version,**kw):return c.post(f'/painel/vendas-manuais/{mid}/alterar',data={'action':action,'version':version,**kw},follow_redirects=False)
    assert mutate('item',0,product_id=env[4],quantity=1).status_code==303
    assert mutate('payment',1,method='cash',amount='3').status_code==303
    assert mutate('close',2).status_code==303
    assert c.post(f'/painel/caixa/{sid}/fechar',data={'counted':'3'},follow_redirects=False).status_code==303
    assert mutate('cancel',3,reason='Cancelamento posterior',refund='1').status_code==409


def test_concurrent_open_and_tenant_checks(env):
    m,c,*_=env;barrier=Barrier(2)
    def action(i):
        client=TestClient(m.app,headers={'Origin':'http://testserver'})
        barrier.wait(timeout=10)
        return client.post('/painel/caixa/abrir',data={'initial':'0','token':'cash424-concurrent-'+str(i)},follow_redirects=False).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:assert sorted(pool.map(action,range(2)))==[303,409]
    with m.db() as db:
        other=db.execute('SELECT id FROM professionals WHERE id<>? LIMIT 1',(env[6]['id'],)).fetchone()[0]
        sid=db.execute('INSERT INTO cash_sessions424(professional_id,opened_by,opened_at,opening_cents,token) VALUES(?,?,?,?,?)',(other,1,cash.stamp(),0,'cash424-other-store')).lastrowid
    assert c.get('/painel/caixa?caixa='+str(sid)).status_code==404
    assert c.post(f'/painel/caixa/{sid}/fechar',data={'counted':'0'},follow_redirects=False).status_code==404


def test_delivery_change_recalculates_with_customer_approval(env):
    m,c,*_=env;o=order(env)
    with m.db() as db:db.execute('UPDATE professionals SET allows_delivery=1,delivery_fee_cents=800 WHERE id=?',(env[6]['id'],))
    data={'customer_name':'Audit','customer_phone':'12999999999','fulfillment_type':'delivery','payment_method':'cash','address':'Rua QA, 1','neighborhood':'Centro'}
    r=c.post(f"/painel/pedidos/{o['id']}/editar",data=data,follow_redirects=False);assert r.status_code==303,r.text
    with m.db() as db:
        proposed=db.execute('SELECT * FROM order_revisions WHERE order_id=?',(o['id'],)).fetchone()
        assert db.execute('SELECT total_cents FROM orders WHERE id=?',(o['id'],)).fetchone()[0]==300
    r=c.post(f"/pedido/{o['tracking_token']}/revisao/{proposed['id']}",data={'decision':'accept'},follow_redirects=False);assert r.status_code==303,r.text
    with m.db() as db:
        result=db.execute('SELECT * FROM orders WHERE id=?',(o['id'],)).fetchone()
        assert result['delivery_fee_cents']==800 and result['total_cents']==1100
    assert c.post(f"/painel/pedidos/{o['id']}/editar",data={**data,'fulfillment_type':'pickup'},follow_redirects=False).status_code==303
    with m.db() as db:revision=db.execute('SELECT MAX(id) FROM order_revisions').fetchone()[0]
    assert c.post(f"/pedido/{o['tracking_token']}/revisao/{revision}",data={'decision':'accept'},follow_redirects=False).status_code==303
    with m.db() as db:
        result=db.execute('SELECT * FROM orders WHERE id=?',(o['id'],)).fetchone()
        assert result['total_cents']==300 and result['delivery_fee_cents']==0 and result['address']==''


def test_postgres_translation_of_migration():
    from nowup_database239 import translate
    class Check:
        def executescript(self,script):
            import sqlglot
            for expression in sqlglot.parse(script,read='sqlite'):
                if expression:assert translate(expression.sql(dialect='sqlite'))[0]
        def commit(self):pass
    cash.initialize(Check())


def test_refund_preserves_prior_snapshot(env):
    m,c,*_=env;sid=open_cash(env,'0');o=order(env,'pix');complete(env,o)
    assert c.post(f'/painel/caixa/{sid}/fechar',data={'counted':'0'},follow_redirects=False).status_code==303
    with m.db() as db:snapshot=db.execute('SELECT snapshot FROM cash_sessions424 WHERE id=?',(sid,)).fetchone()[0]
    second=open_cash(env,'0','cash424-refund-session')
    data={'kind':'order','source_id':o['id'],'value':'2','reason':'Devolução parcial','token':'cash424-partial-refund'}
    for _ in range(2):assert c.post(f'/painel/caixa/{second}/devolver',data=data,follow_redirects=False).status_code==303
    assert c.post(f'/painel/caixa/{second}/devolver',data={**data,'token':'cash424-second-refund'},follow_redirects=False).status_code==400
    with m.db() as db:
        assert db.execute('SELECT snapshot FROM cash_sessions424 WHERE id=?',(sid,)).fetchone()[0]==snapshot
        report=cash.summary(db,dict(db.execute('SELECT * FROM cash_sessions424 WHERE id=?',(second,)).fetchone()))
        assert report['payments']['pix']==-200 and report['sales_cents']==0 and report['expected_cents']==0


def test_500_orders_with_50_workers_and_cash_reconciliation(env,monkeypatch):
    """Accelerated local load; 100 synthetic buyers respect the 5/5min limit."""
    import time
    m,c,url,data,product,buyer,p=env;sid=open_cash(env,'0');now=cash.stamp()
    with m.db() as db:
        buyers=[db.execute("INSERT INTO users(role,name,email,password_hash,created_at) VALUES('customer',?,?,?,?)",('Carga '+str(i),f'cash424-load-{i}@example.invalid','unused',now)).lastrowid for i in range(100)]
    monkeypatch.setattr(m,'current_user',lambda request:({'id':int(request.headers['x-load-buyer']),'role':'customer','name':'Carga','phone':'12999999999'} if request.headers.get('x-load-buyer') else {'id':p['user_id'],'role':'professional'}))
    def submit(i):
        client=TestClient(m.app,headers={'Origin':'http://testserver','X-Load-Buyer':str(buyers[i%100])})
        key='cash424-load-'+str(i).zfill(8);t=time.perf_counter()
        r=client.post(url,data={**data,'payment_method':'cash','request_key':key},follow_redirects=False)
        assert r.status_code==303,r.text
        if i%25==0:
            retry=client.post(url,data={**data,'payment_method':'cash','request_key':key},follow_redirects=False)
            assert retry.headers['location']==r.headers['location']
        return time.perf_counter()-t
    started=time.perf_counter()
    with ThreadPoolExecutor(max_workers=50) as pool:times=list(pool.map(submit,range(500)))
    with m.db() as db:
        rows=db.execute('SELECT o.*,r.request_key FROM orders o JOIN checkout_requests229 r ON r.order_id=o.id ORDER BY o.id').fetchall()
        assert len(rows)==500 and len({r['id'] for r in rows})==500
        assert all(r['customer_id']==buyers[int(r['request_key'].split('-')[-1])%100] for r in rows)
        assert db.execute('SELECT COUNT(*) FROM order_items').fetchone()[0]==500
        assert db.execute('SELECT SUM(quantity*unit_price_cents) FROM order_items').fetchone()[0]==150000
    def finish(pair):
        i,o=pair;client=TestClient(m.app,headers={'Origin':'http://testserver','Accept':'application/json'})
        for state in (['cancelled'] if i%5==0 else ['confirmed','preparing','ready','completed']):
            response=client.post(f"/painel/pedidos/{o['id']}/status",data={'status':state,'reason':'Carga local'})
            assert response.status_code==200,response.text
    with ThreadPoolExecutor(max_workers=50) as pool:list(pool.map(finish,enumerate(rows)))
    with m.db() as db:
        report=cash.summary(db,dict(db.execute('SELECT * FROM cash_sessions424 WHERE id=?',(sid,)).fetchone()))
        assert report['sales_cents']==120000 and report['expected_cents']==120000 and report['sales_count']==400 and not report['pending']
    assert c.post(f'/painel/caixa/{sid}/fechar',data={'counted':'1200'},follow_redirects=False).status_code==303
    times.sort();print('\nCASH424_LOAD '+json.dumps({'orders':500,'workers':50,'completed':400,'cancelled':100,'seconds':round(time.perf_counter()-started,2),'create_p95_seconds':round(times[int(len(times)*.95)],3),'sales_cents':120000}))


def test_unknown_payment_cannot_be_completed(env):
    m,c,*_=env;o=order(env,'on_delivery')
    for status in ('confirmed','preparing','ready'):
        assert c.post(f"/painel/pedidos/{o['id']}/status",data={'status':status},headers={'Accept':'application/json'}).status_code==200
    response=c.post(f"/painel/pedidos/{o['id']}/status",data={'status':'completed'},headers={'Accept':'application/json'})
    assert response.status_code==409
    with m.db() as db:assert db.execute('SELECT status FROM orders WHERE id=?',(o['id'],)).fetchone()[0]=='ready'
