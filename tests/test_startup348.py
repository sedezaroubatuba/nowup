"""Full startup and real opaque-session checks, isolated in a child process."""
import os,subprocess,sys,textwrap
from pathlib import Path


def test_full_startup_and_two_real_buyers_and_merchants(tmp_path):
    program=r'''
import json
from fastapi.testclient import TestClient
import app
with TestClient(app.app,headers={'Origin':'http://testserver'},follow_redirects=False) as lifecycle:
    for path in ('/','/health','/profissionais','/entrar','/cadastro/cliente','/cadastro/profissional','/privacidade','/termos','/contato','/noticias'):
        r=lifecycle.get(path);assert r.status_code==200,(path,r.status_code)
    assert lifecycle.get('/admin/cms').status_code in (401,403)
    with app.db() as c:
        stores=[dict(x) for x in c.execute('SELECT * FROM professionals ORDER BY id LIMIT 2')]
        products=[]
        for i,p in enumerate(stores):
            c.execute("UPDATE professionals SET plan_active='ambos',is_premium=1,offer_mode='menu',admission_status='approved',blocked=0,business_status='open',business_hours='',allows_pickup=1 WHERE id=?",(p['id'],))
            c.execute('UPDATE users SET email_verified=1,password_hash=? WHERE id=?',(app.hash_password('merchant348-password'),p['user_id']))
            products.append(c.execute("INSERT INTO products(professional_id,name,price_cents,extras_mode,created_at,updated_at) VALUES(?,'Private product348',1234,'none',?,?)",(p['id'],app.now_iso(),app.now_iso())).lastrowid)
            c.execute("INSERT INTO users(role,name,email,phone,password_hash,email_verified,created_at) VALUES('customer',?,?,?, ?,1,?)",('Buyer'+str(i),'buyer348-'+str(i)+'@example.com','12999998888',app.hash_password('buyer348-password'),app.now_iso()))
    buyers=[TestClient(app.app,headers={'Origin':'http://testserver'},follow_redirects=False) for _ in range(2)]
    owners=[TestClient(app.app,headers={'Origin':'http://testserver'},follow_redirects=False) for _ in range(2)]
    for i in range(2):
        r=buyers[i].post('/entrar',data={'email':'buyer348-'+str(i)+'@example.com','password':'buyer348-password','tipo':'cliente'})
        assert r.status_code==303 and buyers[i].cookies.get('nowup_session')
        with app.db() as c:email=c.execute('SELECT email FROM users WHERE id=?',(stores[i]['user_id'],)).fetchone()[0]
        r=owners[i].post('/entrar',data={'email':email,'password':'merchant348-password','tipo':'profissional'})
        assert r.status_code==303 and owners[i].cookies.get('nowup_session')
        r=buyers[i].post('/p/'+stores[i]['slug']+'/menu/pedido',data={'customer_name':'Forged buyer','customer_phone':'12988887777','fulfillment_type':'pickup','cart_json':json.dumps([{'id':products[i],'quantity':1}]),'request_key':'startup348-order-'+str(i)})
        assert r.status_code==303,r.text
        target=r.headers['location']
        own=buyers[i].get(target);assert 'Private product348' in own.text
        assert 'Private product348' not in buyers[1-i].get(target).text
        assert 'Private product348' in owners[i].get(target).text
        assert 'Private product348' not in owners[1-i].get(target).text
        with app.db() as c:order=c.execute('SELECT * FROM orders ORDER BY id DESC LIMIT 1').fetchone();oid=order['id'];assert order['customer_name']=='Buyer'+str(i)
        assert buyers[1-i].get('/pedidos/'+str(oid)+'/conversa').status_code in (401,403,404)
        assert owners[1-i].get('/pedidos/'+str(oid)+'/conversa').status_code in (401,403,404)
        assert buyers[i].get('/pedidos/'+str(oid)+'/conversa').status_code==200
    print('Full startup; ten public pages; real login; two buyers and two merchants; order privacy and chat isolation passed.')
'''
    env={**os.environ,'NOWUP_DB_ENGINE':'sqlite','NOWUP_DB':str(tmp_path/'db'),'NOWUP_UPLOAD_DIR':str(tmp_path/'uploads'),'NOWUP_ADMIN_EMAIL':'startup348@example.invalid','NOWUP_ADMIN_PASSWORD':'startup348-private-password','NOWUP_HTTPS':'0','NOWUP_BACKUP_ENABLED':'0','BREVO_API_KEY':'','NOWUP_EMAIL_FROM':''}
    r=subprocess.run([sys.executable,'-c',program],cwd=Path(__file__).resolve().parents[1],env=env,capture_output=True,text=True,timeout=90)
    assert r.returncode==0,r.stdout+r.stderr
