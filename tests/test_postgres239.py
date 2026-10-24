"""Run integration checks only with an explicit disposable PostgreSQL test URL.

Use a separate pytest invocation for these tests. No production database is used.
"""
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
import pytest
from nowup_database239 import translate,Row


def test_literal_parameters_conflicts_and_rows():
    statement,_=translate("SELECT '?' AS text, name FROM users WHERE id=? AND name LIKE ?")
    assert "'?'" in statement and statement.count('%s')==2 and 'ILIKE' in statement
    statement,_=translate('INSERT INTO site_settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value')
    assert 'NULLS FIRST' not in statement
    row=Row(('id','id','name'),(1,2,'José'))
    assert row['id']==1 and row[1]==2 and dict(row)['name']=='José'


@pytest.fixture(scope='module')
def pg(tmp_path_factory):
    url=os.getenv('NOWUP_TEST_POSTGRES_URL')
    if not url:pytest.skip('Disposable PostgreSQL test URL not configured')
    import psycopg
    from psycopg import sql
    from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode
    from uuid import uuid4
    schema='test_nowup_'+uuid4().hex
    with psycopg.connect(url,autocommit=True) as conn:conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    parsed=urlsplit(url);query=dict(parse_qsl(parsed.query));query['options']='-csearch_path='+schema
    scoped=urlunsplit(parsed._replace(query=urlencode(query)))
    root=tmp_path_factory.mktemp('postgres239');source=root/'source.db';uploads=root/'uploads';uploads.mkdir()
    source_env={**os.environ,'NOWUP_DB_ENGINE':'sqlite','NOWUP_DB':str(source),'NOWUP_UPLOAD_DIR':str(uploads),'NOWUP_ADMIN_EMAIL':'admin@test.invalid','NOWUP_ADMIN_PASSWORD':'isolated-test-only'}
    source_code="""
import app
for callback in app.app.router.on_startup:
 if callback.__name__!='start':callback()
app.nowup_push75.initialize()
app.nowup_alerts112.initialize()
"""
    subprocess.run([sys.executable,'-c',source_code],env=source_env,check=True,cwd=Path(__file__).resolve().parents[1],stdout=subprocess.DEVNULL)
    with sqlite3.connect(source) as conn:
        for table in [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]:
            for column in [r[1] for r in conn.execute('PRAGMA table_info("'+table+'")') if 'filename' in r[1]]:
                conn.execute('UPDATE "'+table+'" SET "'+column+'"=\'\'')
    old={key:os.environ.get(key) for key in ['NOWUP_DB_ENGINE','DATABASE_URL','NOWUP_DB','NOWUP_UPLOAD_DIR','NOWUP_ADMIN_EMAIL','NOWUP_ADMIN_PASSWORD','NOWUP_PG_POOL_SIZE','NOWUP_HTTPS']}
    os.environ.update(NOWUP_DB_ENGINE='postgres',DATABASE_URL=scoped,NOWUP_DB=str(source),NOWUP_UPLOAD_DIR=str(uploads),NOWUP_ADMIN_EMAIL='admin@test.invalid',NOWUP_ADMIN_PASSWORD='isolated-test-only',NOWUP_PG_POOL_SIZE=os.getenv('NOWUP_TEST_POOL_SIZE','4'),NOWUP_HTTPS='0')
    from nowup_database239 import close_pool
    close_pool()
    from migrate_postgres239 import migrate
    report=migrate(source,root/'report.json')
    import app
    for callback in app.app.router.on_startup:
        if callback.__name__!='start':callback()
    app.nowup_push75.initialize()
    app.nowup_alerts112.initialize()
    from fastapi.testclient import TestClient
    client=TestClient(app.app,headers={'Origin':'http://testserver'})
    try:yield app,client,report,source,root
    finally:
        close_pool()
        for key,value in old.items():
            if value is None:os.environ.pop(key,None)
            else:os.environ[key]=value
        with psycopg.connect(url,autocommit=True) as conn:conn.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))


def test_verified_migration_and_read_pages(pg):
    m,client,report,source,_=pg
    assert report['verified'] and len(report['tables'])>50
    with sqlite3.connect(source) as original:
        for table,result in report['tables'].items():assert original.execute('SELECT COUNT(*) FROM "'+table+'"').fetchone()[0]==result['rows']
    for path in ['/','/profissionais','/p/aloha-surf-shop','/noticias','/contato']:
        response=client.get(path);assert response.status_code==200,(path,response.text[:100])
    from migrate_postgres239 import migrate
    from nowup_database239 import close_pool
    close_pool()
    with pytest.raises(ValueError,match='vazio'):migrate(source)


def test_generated_ids_conflicts_and_foreign_keys(pg):
    m,_,_,_,_=pg
    with m.db() as c:
        c.execute("INSERT OR IGNORE INTO site_settings VALUES('pg239-test','one')")
        c.execute("INSERT OR IGNORE INTO site_settings VALUES('pg239-test','two')")
        assert c.execute("SELECT value FROM site_settings WHERE key='pg239-test'").fetchone()[0]=='one'
        before=c.execute('SELECT MAX(id) FROM categories').fetchone()[0]
        inserted=c.execute("INSERT INTO categories(name,slug) VALUES('PG category','pg239-category')").lastrowid
        assert inserted>before
        user=c.execute('SELECT id FROM users ORDER BY id LIMIT 1').fetchone()[0]
        c.execute('INSERT OR REPLACE INTO push_subscriptions VALUES(?,?,?,?)',('https://test.invalid/239',user,'old','{}'))
        c.execute('INSERT OR REPLACE INTO push_subscriptions VALUES(?,?,?,?)',('https://test.invalid/239',user,'new','{}'))
        assert c.execute('SELECT session_hash FROM push_subscriptions WHERE endpoint=?',('https://test.invalid/239',)).fetchone()[0]=='new'
    c=m.db()
    try:
        with pytest.raises(sqlite3.IntegrityError):c.execute("INSERT INTO products(professional_id,name,created_at,updated_at) VALUES(-123,'invalid','now','now')")
        c.rollback()
    finally:c.close()


def test_authenticated_reports_settings_and_replayed_checkout(pg):
    import json,secrets
    from datetime import datetime,timedelta,timezone
    m,client,_,_,_=pg;now=datetime.now(timezone.utc);stamp=now.isoformat();expiry=(now+timedelta(days=2)).isoformat();absolute=(now+timedelta(days=90)).isoformat()
    with m.db() as c:
        pro=c.execute('SELECT * FROM professionals ORDER BY id LIMIT 1').fetchone()
        c.execute("UPDATE professionals SET plan_active='ambos',is_premium=1,offer_mode='menu',business_status='open',business_hours='',allows_pickup=1,minimum_order_cents=0 WHERE id=?",(pro['id'],))
        product=c.execute("INSERT INTO products(professional_id,name,category,price_cents,created_at,updated_at,extras_mode) VALUES(?,'Lanche de teste','Lanches',2390,?,?,'none')",(pro['id'],stamp,stamp)).lastrowid
        customer=c.execute("INSERT INTO users(role,name,email,password_hash,created_at) VALUES('customer','Cliente de teste',?,'unused',?)",('pg239-'+secrets.token_hex(6)+'@test.invalid',stamp)).lastrowid
        c.execute('INSERT INTO sessions(token,user_id,expires_at,absolute_expires_at238) VALUES(?,?,?,?)',('customer239',customer,expiry,absolute))
        c.execute('INSERT INTO sessions(token,user_id,expires_at,absolute_expires_at238) VALUES(?,?,?,?)',('merchant239',pro['user_id'],expiry,absolute))
    client.cookies.set('nowup_session','merchant239')
    assert client.get('/painel').status_code==200
    assert client.get('/').status_code==200
    assert client.get('/p/'+pro['slug']).status_code==200
    assert client.post('/painel/cardapio/exibicao',data={'carousel_layout235':'pair'},follow_redirects=False).status_code==303
    client.cookies.set('nowup_session','customer239')
    payload={'customer_name':'Cliente teste','customer_phone':'12999999999','fulfillment_type':'pickup','cart_json':json.dumps([{'id':product,'quantity':2,'price':1}]),'request_key':'postgres-test-key239'}
    a=client.post('/p/'+pro['slug']+'/menu/pedido',data=payload,follow_redirects=False)
    assert a.status_code==303,a.text
    b=client.post('/p/'+pro['slug']+'/menu/pedido',data=payload,follow_redirects=False)
    assert b.status_code==303 and a.headers['location']==b.headers['location']
    with m.db() as c:
        orders=c.execute('SELECT total_cents FROM orders WHERE customer_id=?',(customer,)).fetchall()
        assert len(orders)==1 and orders[0][0]==4780
    assert client.get(a.headers['location']).status_code==200
    client.cookies.clear()


def test_postgres_native_backup_archive(pg):
    import shutil,zipfile,json
    if not shutil.which('pg_dump') or not shutil.which('pg_restore'):pytest.skip('Native PostgreSQL client required')
    import nowup_backup
    from restore_backup import stage_backup
    m,_,_,_,root=pg
    asset=m.UPLOAD_DIR/'native239.txt';asset.write_text('Arquivo de teste')
    with m.db() as c:c.execute("UPDATE products SET image_filename='native239.txt' WHERE id=(SELECT MIN(id) FROM products)")
    directory=root/'native-backup';directory.mkdir()
    archive=nowup_backup.create_archive(directory)
    staged=root/'native-staged';stage_backup(archive,staged)
    manifest=json.loads((staged/'manifest.json').read_text())
    assert manifest['backend']=='postgres' and manifest['row_counts']['users']>0
    assert (staged/'uploads/native239.txt').read_text()=='Arquivo de teste'
    import psycopg
    from psycopg import sql
    from urllib.parse import urlsplit,urlunsplit
    from uuid import uuid4
    from restore_postgres239 import restore
    source_url=os.environ['DATABASE_URL'];new_database='test_restore_'+uuid4().hex
    with psycopg.connect(source_url,autocommit=True) as connection:connection.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(new_database)))
    os.environ['DATABASE_URL']=urlunsplit(urlsplit(source_url)._replace(path='/'+new_database))
    try:
        assert restore(staged,True)==len(manifest['row_counts'])
        with pytest.raises(ValueError,match='contém tabelas'):restore(staged,True)
    finally:
        os.environ['DATABASE_URL']=source_url
        with psycopg.connect(source_url,autocommit=True) as connection:connection.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(new_database)))


@pytest.mark.skipif(os.getenv('NOWUP_TEST_EMBEDDED')=='1',reason='Requires independent native PostgreSQL sessions')
def test_concurrent_checkout_key_creates_one_order(pg):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from datetime import datetime,timezone
    from nowup_checkout229 import begin_checkout,remember_checkout
    m,_,_,_,_=pg
    with m.db() as c:
        customer=c.execute("SELECT id FROM users WHERE role='customer' ORDER BY id LIMIT 1").fetchone()[0]
        professional=c.execute('SELECT id FROM professionals ORDER BY id LIMIT 1').fetchone()[0]
    barrier=Barrier(2)
    def submit(index):
        c=m.db()
        try:
            barrier.wait(timeout=10)
            existing,key,digest=begin_checkout(c,customer,professional,'parallel-request-key239',{'cart':'[]'})
            if existing:c.rollback();return existing
            stamp=datetime.now(timezone.utc).isoformat();token='parallel239-'+str(index)
            oid=c.execute("INSERT INTO orders(professional_id,customer_id,customer_name,created_at,updated_at,tracking_token) VALUES(?,?,'Teste paralelo',?,?,?)",(professional,customer,stamp,stamp,token)).lastrowid
            remember_checkout(c,customer,professional,key,digest,oid,stamp);c.commit();return token
        finally:c.close()
    with ThreadPoolExecutor(max_workers=2) as executor:tokens=list(executor.map(submit,[1,2]))
    assert tokens[0]==tokens[1]
    with m.db() as c:assert c.execute("SELECT COUNT(*) FROM orders WHERE tracking_token LIKE 'parallel239-%'").fetchone()[0]==1
