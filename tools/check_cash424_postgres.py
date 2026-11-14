"""Real PostgreSQL cash contention test; only a disposable local test server."""
import os,sys,uuid
from pathlib import Path
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import psycopg
from psycopg import sql
from fastapi import FastAPI
from fastapi.testclient import TestClient
from nowup_database239 import PostgresConnection,row_factory
from nowup_cash424 import initialize,install,summary
url=os.environ['NOWUP_TEST_PG_URL424']
if urlparse(url).hostname not in ('localhost','127.0.0.1','::1'):
    raise RuntimeError('Este teste aceita somente PostgreSQL local e descartável.')
schema='cash424_'+uuid.uuid4().hex
admin=psycopg.connect(url,autocommit=True)
admin.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
def db():
    raw=psycopg.connect(url,autocommit=True,row_factory=row_factory)
    raw.execute(sql.SQL('SET search_path TO {}').format(sql.Identifier(schema)))
    return PostgresConnection(raw)
try:
    with db() as c:
        c.execute('CREATE TABLE professionals(id INTEGER PRIMARY KEY,user_id INTEGER,blocked INTEGER,display_name TEXT)')
        c.execute('CREATE TABLE orders(id INTEGER PRIMARY KEY,professional_id INTEGER,status TEXT,payment_method TEXT,total_cents INTEGER,order_code TEXT,created_at TEXT,updated_at TEXT)')
        c.execute('CREATE TABLE order_status_history(id INTEGER PRIMARY KEY,order_id INTEGER,status TEXT,created_at TEXT)')
        c.execute('CREATE TABLE manual_sales107(id INTEGER PRIMARY KEY,professional_id INTEGER,status TEXT,label TEXT,total_cents INTEGER,closed_at TEXT,refund_recorded INTEGER)')
        c.execute('CREATE TABLE manual_payments107(id INTEGER PRIMARY KEY,sale_id INTEGER,method TEXT,cents INTEGER,created_at TEXT)')
        c.execute("INSERT INTO professionals VALUES(1,1,0,'QA descartável')")
        initialize(c)
    app=FastAPI();install({'app':app,'db':db,'require_user':lambda request,role:{'id':1,'role':'professional'}})
    def opening(i):
        client=TestClient(app)
        return client.post('/painel/caixa/abrir',data={'initial':'100','token':'cash424-postgres-open-'+str(i)},follow_redirects=False).status_code
    with ThreadPoolExecutor(max_workers=20) as pool:codes=list(pool.map(opening,range(20)))
    assert codes.count(303)==1 and codes.count(409)==19,codes
    with db() as c:
        sid=c.execute('SELECT id FROM cash_sessions424').fetchone()[0]
        now=datetime.now(timezone.utc).isoformat()
        for i,(method,cents) in enumerate([('cash',5000),('pix',8000),('credit',12000)],1):
            c.execute('INSERT INTO orders VALUES(?,1,?,?,?,?,?,?)',(i,'completed',method,cents,'QA-'+str(i),now,now))
            c.execute('INSERT INTO order_status_history(order_id,status,created_at) VALUES(?,?,?)',(i,'completed',now))
    client=TestClient(app)
    for kind,value in [('supply','20'),('withdrawal','30')]:
        payload={'kind':kind,'value':value,'reason':'QA','token':'cash424-postgres-move-'+kind}
        for _ in range(2):assert client.post(f'/painel/caixa/{sid}/movimento',data=payload,follow_redirects=False).status_code==303
    with db() as c:
        s=dict(c.execute('SELECT * FROM cash_sessions424 WHERE id=?',(sid,)).fetchone());r=summary(c,s)
        assert r['sales_cents']==25000 and r['expected_cents']==14000 and r['sales_count']==3
    assert client.post(f'/painel/caixa/{sid}/fechar',data={'counted':'140'},follow_redirects=False).status_code==303
    assert client.post(f'/painel/caixa/{sid}/fechar',data={'counted':'140'},follow_redirects=False).status_code==409
    with db() as c:
        s=dict(c.execute('SELECT * FROM cash_sessions424 WHERE id=?',(sid,)).fetchone());assert summary(c,s)['sales_cents']==25000
        assert c.execute('SELECT COUNT(*) FROM cash_sources424').fetchone()[0]==3
    print('PASS PostgreSQL: 20 concurrent opens, single session, idempotent movements, R$250 sales, R$140 cash and immutable closing.')
finally:
    admin.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)));admin.close()
