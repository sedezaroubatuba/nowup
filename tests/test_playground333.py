"""Exercise the real sandbox child and the production routing boundary."""
from datetime import datetime,timedelta,timezone
from pathlib import Path
import os
import sqlite3
import pytest
from fastapi.testclient import TestClient
from test_merchant228 import env
from nowup_test333 import child_environment, Playground


def test_environment_has_no_production_credentials(tmp_path,monkeypatch):
    for name in ('DATABASE_URL','BREVO_API_KEY','ASAAS_API_KEY','AWS_ACCESS_KEY_ID','REDIS_URL'):
        monkeypatch.setenv(name,'production-secret')
    values=child_environment(tmp_path,'private-secret')
    assert all(name not in values for name in ('DATABASE_URL','BREVO_API_KEY','ASAAS_API_KEY','AWS_ACCESS_KEY_ID','REDIS_URL'))
    assert values['NOWUP_DB_ENGINE']=='sqlite'
    assert values['NOWUP_DB']==str(tmp_path/'nowup.db')
    assert values['NOWUP_UPLOAD_DIR']==str(tmp_path/'uploads')


def test_real_sandbox_and_production_separation(env,monkeypatch,tmp_path):
    # The real child blocks all external sockets. Mock only DNS deliverability
    # in this test subprocess; keep the real email syntax validator and network guard.
    mockdir=tmp_path/'child-test-pythonpath';mockdir.mkdir()
    (mockdir/'sitecustomize.py').write_text("import os\nif os.getenv('NOWUP_TEST_CHILD333') == '1':\n import email_validator\n original=email_validator.validate_email\n def validate_email(*args,**kwargs):\n  kwargs['check_deliverability']=False\n  return original(*args,**kwargs)\n email_validator.validate_email=validate_email\n")
    monkeypatch.syspath_prepend(str(mockdir))
    main,_,_,store_id,_=env
    with main.db() as c:
        admin=c.execute("SELECT id FROM users WHERE role='admin'").fetchone()[0]
        c.execute('INSERT INTO sessions(token,user_id,expires_at) VALUES(?,?,?)',('admin-333',admin,(datetime.now(timezone.utc)+timedelta(minutes=20)).isoformat()))
        before_users=c.execute('SELECT count(*) FROM users').fetchone()[0]
        before_orders=c.execute('SELECT count(*) FROM orders').fetchone()[0]
        c.commit()
    client=TestClient(main.app,headers={'Origin':'http://testserver'},follow_redirects=False)
    assert client.get('/admin/modo-teste').status_code==401
    client.cookies.set('nowup_session','merchant-test')
    assert client.post('/admin/modo-teste/entrar').status_code==403
    client.cookies.set('nowup_session','admin-333')
    assert client.get('/admin/modo-teste').status_code==200
    response=client.post('/admin/modo-teste/entrar')
    assert response.status_code==303, response.text
    assert client.cookies.get('nowup_session')=='admin-333'
    assert client.get('/__controle333').status_code==200
    result=client.post('/cadastro/cliente',data=dict(name='Cliente exclusivo do teste 333',email='only-test333@example.com',phone='12999998888',password='password333',password_confirm='password333',accept_terms='1',address='Rua teste 333',neighborhood='Centro',city='Ubatuba',state='SP'))
    assert result.status_code==303
    assert result.headers['location']=='/__controle333'
    assert 'Cliente exclusivo do teste 333' in client.get('/__controle333').text
    # The sandbox ADM is authenticated using a different, prefixed cookie.
    response=client.get('/admin/super')
    assert response.status_code==200
    assert 'TESTE -' in response.text and '/static/test333-guard.js' in response.text
    result=client.post('/__loja333',data={'name':'Loja cardápio teste 333','plan':'cardapio','offer':'menu'})
    assert result.status_code==303, result.text
    panel=client.get('/painel')
    assert panel.status_code==200
    assert 'Loja cardápio teste 333' in panel.text
    assert 'TESTE -' in panel.text
    # Logout of a simulated profile must leave the production session intact.
    assert client.post('/sair').status_code==303
    assert client.cookies.get('nowup_session')=='admin-333'
    assert client.post('/admin/modo-teste/sair').status_code==303
    assert client.get('/admin/super').status_code==200
    # A form left open in a sandbox tab cannot mutate production after exit.
    assert client.post('/cliente/comunicacoes?__nu333_test=1').status_code==409
    assert client.post('/cliente/comunicacoes',headers={'X-Nowup-Test333':'1'}).status_code==409
    with main.db() as c:
        assert c.execute('SELECT count(*) FROM users').fetchone()[0]==before_users
        assert c.execute('SELECT count(*) FROM orders').fetchone()[0]==before_orders
        assert not c.execute("SELECT 1 FROM users WHERE email='only-test333@example.com'").fetchone()
