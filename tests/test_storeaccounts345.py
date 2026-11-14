from datetime import datetime,timedelta,timezone
import pytest
from fastapi.testclient import TestClient
from test_merchant228 import env

@pytest.fixture(scope='module')
def setup345(env):
    main,_,_,a,b=env
    main.nowup_push75.initialize();main.nowup_alerts112.initialize()
    sent=[]
    patch=pytest.MonkeyPatch()
    patch.setattr(main,'send_email',lambda *args,**kw: sent.append(args) or True)
    patch.setattr(main,'email_service_configured',lambda:True)
    patch.setattr(main,'normalize_email',lambda value:value.strip().lower() if '@' in value else '')
    patch.setenv('NOWUP_BASE_URL','http://testserver')
    with main.db() as c:
        c.execute("UPDATE professionals SET plan_active='cardapio',is_premium=1,offer_mode='menu',admission_status='approved',blocked=0 WHERE id IN (?,?)",(a,b))
        stores=[dict(c.execute('SELECT * FROM professionals WHERE id=?',(pid,)).fetchone()) for pid in (a,b)]
        uid=c.execute("INSERT INTO users(role,name,email,phone,password_hash,email_verified,created_at) VALUES('customer','Marketplace','shared345@example.com','12999998888',?,1,?)",(main.hash_password('market-password345'),main.now_iso())).lastrowid
        c.execute('INSERT INTO sessions(token,user_id,expires_at) VALUES(?,?,?)',('market345',uid,(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()));c.commit()
    yield main,stores,sent
    patch.undo()


def signup(client,p,name,password):
    return client.post('/p/'+p['slug']+'/cadastro',data=dict(name=name,email='shared345@example.com',phone='12999998888',password=password,password_confirm=password,accept_terms='1',marketing_email309='1',marketing_whatsapp309='1',address='Rua teste 345',neighborhood='Centro',city='Ubatuba',state='SP'))


def test_accounts_sessions_and_logout_are_store_exclusive(setup345):
    main,(a,b),sent=setup345
    client=TestClient(main.app,headers={'Origin':'http://testserver'},follow_redirects=False)
    client.cookies.set('nowup_session','market345')
    path=lambda p,tail:'/p/'+p['slug']+'/'+tail
    # Marketplace login never signs a customer into an exclusive storefront.
    assert 'data-login-required="1"' in client.get(path(a,'menu')).text
    for p,name,password in ((a,'Cliente exclusivo A','store-a-password345'),(b,'Cliente exclusivo B','store-b-password345')):
        r=signup(client,p,name,password);assert r.status_code==303,r.text
        assert r.headers['location']==path(p,'aguardando')
        with main.db() as c:
            row=c.execute('SELECT * FROM users WHERE customer_store345=?',(p['id'],)).fetchone()
            assert row['customer_email345']=='shared345@example.com'
            assert not main.nowup_marketing309.eligible(c,row['id'],'email')
            assert not main.nowup_marketing309.eligible(c,row['id'],'whatsapp')
            token=row['verification_token']
        assert path(p,'verificar-email') in sent[-1][3]
        assert sent[-1][0]=='shared345@example.com'
        other=b if p['id']==a['id'] else a
        assert 'erro=verificacao' in client.get(path(other,'verificar-email')+'?token='+token).headers['location']
        assert 'verificado=1' in client.get(path(p,'verificar-email')+'?token='+token).headers['location']
    # Same email, three distinct account IDs and passwords.
    with main.db() as c:
        rows=c.execute("SELECT id FROM users WHERE email='shared345@example.com' OR customer_email345='shared345@example.com'").fetchall()
        assert len(rows)==3 and len({r['id'] for r in rows})==3
    r=client.post(path(a,'entrar'),data={'email':'shared345@example.com','password':'store-a-password345'})
    assert r.status_code==303 and r.headers['location']==path(a,'cardapio')
    name='nowup_loja345_'+str(a['id'])
    token=client.cookies.get(name)
    assert token and client.cookies.get('nowup_session')=='market345'
    assert 'Path='+path(a,'').rstrip('/')+';' in r.headers['set-cookie']
    assert 'data-login-required="0"' in client.get(path(a,'menu')).text
    assert 'data-login-required="1"' in client.get(path(b,'menu')).text
    assert 'data-login-required="0"' in client.get('/p/'+a['slug']).text
    assert client.get(path(a,'pedidos')).status_code==200
    with main.db() as c:
        c.execute('UPDATE sessions SET expires_at=? WHERE token=?',((datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),token));c.commit()
    renewed=client.get(path(a,'menu'))
    assert name+'=' in renewed.headers.get('set-cookie','')
    assert 'nowup_session=' not in renewed.headers.get('set-cookie','')
    assert client.get(path(b,'pedidos')).status_code==303
    # Moving the opaque token into another cookie cannot escape server scope.
    forged=TestClient(main.app,headers={'Origin':'http://testserver'},follow_redirects=False)
    forged.cookies.set('nowup_session',token)
    assert forged.get('/cliente').status_code==401
    forged.cookies.set('nowup_loja345_'+str(b['id']),token,path=path(b,''))
    assert forged.get(path(b,'pedidos')).status_code==303
    # Wrong-store and marketplace credentials do not authenticate at this store.
    assert 'erro=1' in client.post(path(b,'entrar'),data={'email':'shared345@example.com','password':'store-a-password345'}).headers['location']
    assert 'erro=1' in client.post(path(b,'entrar'),data={'email':'shared345@example.com','password':'market-password345'}).headers['location']
    assert client.post(path(b,'entrar'),data={'email':'shared345@example.com','password':'store-b-password345'}).status_code==303
    assert client.post(path(a,'sair')).status_code==303
    assert not client.cookies.get(name)
    assert client.cookies.get('nowup_loja345_'+str(b['id']))
    assert client.cookies.get('nowup_session')=='market345'
    assert client.get(path(b,'pedidos')).status_code==200
    # Recovery for B cannot change A or the marketplace password.
    assert client.post(path(b,'recuperar-senha'),data={'email':'shared345@example.com'}).status_code==303
    import re,html
    link=html.unescape(re.search('href="([^"]+)"',sent[-1][3]).group(1))
    from urllib.parse import urlsplit,parse_qs
    raw=parse_qs(urlsplit(link).query)['token'][0]
    assert 'erro=expirado' in client.post(path(a,'redefinir-senha'),data={'token':raw,'password':'new-password345','password_confirm':'new-password345'}).headers['location']
    assert 'senha_redefinida=1' in client.post(path(b,'redefinir-senha'),data={'token':raw,'password':'new-password345','password_confirm':'new-password345'}).headers['location']
    assert client.get(path(b,'pedidos')).status_code==303
    assert client.get('/cliente').status_code==200
    assert 'erro=1' not in client.post(path(a,'entrar'),data={'email':'shared345@example.com','password':'store-a-password345'}).headers['location']


def test_store_forms_keep_brand_and_scope(setup345):
    main,(a,b),_=setup345
    client=TestClient(main.app,headers={'Origin':'http://testserver'},follow_redirects=False)
    for tail,action in [('entrar','entrar?tipo=cliente'),('cadastro','cadastro'),('recuperar-senha','recuperar-senha'),('aguardando','reenviar-verificacao')]:
        r=client.get('/p/'+a['slug']+'/'+tail)
        assert r.status_code==200,r.text
        assert '/p/'+a['slug']+'/'+action in r.text
        assert 'store-app256' in r.text
    # A return cookie left by the old version cannot capture a marketplace login.
    client.cookies.set('nowup_store_return256',a['slug'])
    r=client.post('/entrar',data={'email':'shared345@example.com','password':'market-password345','tipo':'cliente'})
    assert r.status_code==303 and r.headers['location']=='/'


def test_exclusive_store_exposes_merchant_entry_without_mixing_accounts(setup345):
    from bs4 import BeautifulSoup
    main,(a,b),_=setup345
    client=TestClient(main.app,headers={'Origin':'http://testserver'},follow_redirects=False)
    for tail in ('menu?loja=1','entrar?tipo=cliente'):
        page=client.get('/p/'+a['slug']+'/'+tail)
        soup=BeautifulSoup(page.text,'html.parser')
        assert soup.select_one('.storeapp-actions256 a[href="/entrar?tipo=profissional"]')
        assert '/static/store-session345.js?v=420' in page.text
    login=BeautifulSoup(page.text,'html.parser')
    form=login.select_one('#nowup-login-form349')
    assert form['action']=='/p/'+a['slug']+'/entrar?tipo=cliente'
    assert form.select_one('[name="tipo"]')['value']=='cliente'
    assert login.select_one('.storeapp-merchant405 a')['href']=='/entrar?tipo=profissional'
    merchant_page=client.get('/entrar?tipo=profissional')
    merchant_form=BeautifulSoup(merchant_page.text,'html.parser').select_one('#nowup-login-form349')
    assert merchant_form['action']=='/entrar'
    assert merchant_form.select_one('[name="tipo"]')['value']=='profissional'

    # A customer password cannot become a merchant session via the new link.
    denied=client.post('/entrar',data={'email':'shared345@example.com','password':'market-password345','tipo':'profissional'})
    assert 'erro=perfil' in denied.headers['location']
    assert 'nowup_session=' not in denied.headers.get('set-cookie','')
    assert client.get('/painel/kanban228').status_code==401

    # Authentication uses the existing central owner account, even when the
    # entry link was reached from another shop. The panel stays the owner's.
    with main.db() as c:
        owner=c.execute('SELECT * FROM users WHERE id=?',(a['user_id'],)).fetchone()
        c.execute('UPDATE users SET password_hash=?,email_verified=1 WHERE id=?',(main.hash_password('merchant-entry405-password'),owner['id']))
    response=client.post('/entrar',data={'email':owner['email'],'password':'merchant-entry405-password','tipo':'profissional'})
    assert response.status_code==303 and response.headers['location']=='/painel'
    assert 'HttpOnly' in response.headers['set-cookie']
    assert not client.cookies.get('nowup_loja345_'+str(a['id']))
    with main.db() as c:
        session=c.execute('SELECT user_id,store_id345 FROM sessions WHERE token=?',(client.cookies.get('nowup_session'),)).fetchone()
        assert session['user_id']==a['user_id'] and not session['store_id345']
    assert client.get('/painel/kanban228').status_code==200
    for p in (a,b):
        page=client.get('/p/'+p['slug']+'/entrar')
        soup=BeautifulSoup(page.text,'html.parser')
        assert soup.select_one('.storeapp-actions256 a[href="/painel"]')
        assert soup.select_one('.storeapp-merchant405 a')['href']=='/painel'
        assert 'data-enable-order-alerts' not in page.text
    # Global merchant alerts continue to exist in the authenticated panel.
    assert 'data-enable-order-alerts' in client.get('/painel').text


def test_order_chat_and_tracking_use_store_scope(setup345):
    main,(a,b),_=setup345
    client=TestClient(main.app,headers={'Origin':'http://testserver'},follow_redirects=False)
    assert client.post('/p/'+a['slug']+'/entrar',data={'email':'shared345@example.com','password':'store-a-password345'}).status_code==303
    with main.db() as c:
        uid=c.execute('SELECT id FROM users WHERE customer_store345=?',(a['id'],)).fetchone()[0]
        stamp=main.now_iso()
        oid=c.execute("INSERT INTO orders(professional_id,customer_id,customer_name,customer_phone,status,total_cents,created_at,updated_at,tracking_token,order_code) VALUES(?,?,?,'12999998888','new',500,?,?,?,?)",(a['id'],uid,'Cliente A',stamp,stamp,'tracking-exclusive345','NU-EX345')).lastrowid
        c.commit()
    prefix='/p/'+a['slug']
    assert client.get(prefix+'/pedido/tracking-exclusive345').status_code==200
    chat=prefix+'/pedidos/'+str(oid)+'/conversa'
    assert client.get(chat).status_code==200
    assert client.post(chat,data={'message':'Mensagem exclusiva A'}).status_code==200
    assert client.get(chat).json()['messages'][-1]['body']=='Mensagem exclusiva A'
    assert client.get('/pedidos/'+str(oid)+'/conversa').status_code==401
    assert client.get('/p/'+b['slug']+'/pedidos/'+str(oid)+'/conversa').status_code==404
    assert client.get(prefix+'/pedido/tracking-exclusive345/status').status_code==200
    assert client.get('/p/'+b['slug']+'/pedido/tracking-exclusive345/status').status_code==404


def test_scoped_customer_can_checkout_without_marketplace_login(setup345,monkeypatch):
    import json
    main,(a,b),_=setup345
    monkeypatch.setattr(main,'shop_status',lambda p:{'open':True,'label':'Aberto','reason':'','next_open':''})
    client=TestClient(main.app,headers={'Origin':'http://testserver'},follow_redirects=False)
    assert client.post('/p/'+a['slug']+'/entrar',data={'email':'shared345@example.com','password':'store-a-password345'}).status_code==303
    assert not client.cookies.get('nowup_session')
    with main.db() as c:
        stamp=main.now_iso()
        product=c.execute("INSERT INTO products(professional_id,name,category,price_cents,available,created_at,updated_at) VALUES(?,'Produto exclusivo345','Teste',700,1,?,?)",(a['id'],stamp,stamp)).lastrowid
        uid=c.execute('SELECT id FROM users WHERE customer_store345=?',(a['id'],)).fetchone()[0]
        c.execute('UPDATE professionals SET allows_pickup=1,minimum_order_cents=0 WHERE id=?',(a['id'],))
        c.execute("INSERT INTO store_menu257(professional_id,whatsapp,mode) VALUES(?,'','both')",(a['id'],))
        c.commit()
    data={'customer_name':'Cliente A','customer_phone':'12999998888','cart_json':json.dumps([{'id':product,'quantity':1}]),'fulfillment_type':'pickup','payment_method':'cash','request_key':'store345-exclusive-checkout'}
    r=client.post('/p/'+a['slug']+'/menu/whatsapp',data=data)
    assert r.status_code==200,r.text
    result=r.json();assert result['recorded'] and result['total_cents']==700
    assert result['redirect'].startswith('/p/'+a['slug']+'/pedido/')
    assert client.get(result['redirect']).status_code==200
    with main.db() as c:
        order=c.execute('SELECT professional_id,customer_id FROM orders ORDER BY id DESC LIMIT 1').fetchone()
        assert (order['professional_id'],order['customer_id'])==(a['id'],uid)
    confirmed=client.get('/p/'+a['slug']+'/cart-completion345?request_key='+data['request_key'])
    assert confirmed.status_code==200 and confirmed.json()['confirmed']
    assert client.get('/api/cart-completion247?request_key='+data['request_key']).status_code==401
    assert client.get('/p/'+a['slug']+'/cliente/avisos').status_code==200


def test_support_push_stays_in_the_private_store_account(setup345):
    main,(a,b),_=setup345
    import secrets,json
    expiry=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
    users=[];clients=[]
    for p in (a,b):
        with main.db() as c:
            uid=c.execute("INSERT INTO users(role,name,email,password_hash,email_verified,customer_store345,customer_email345,created_at) VALUES('customer','Push private',?,'unused',1,?,'push@example.com',?)",(secrets.token_hex(12)+'@nowup.local',p['id'],main.now_iso())).lastrowid
            token=secrets.token_urlsafe(32)
            c.execute('INSERT INTO sessions(token,user_id,expires_at,store_id345) VALUES(?,?,?,?)',(token,uid,expiry,p['id']))
        client=TestClient(main.app,headers={'Origin':'http://testserver'},follow_redirects=False)
        client.cookies.set('nowup_loja345_'+str(p['id']),token,path='/p/'+p['slug'])
        users.append(uid);clients.append(client)
    route='/p/'+a['slug']+'/suporte'
    response=clients[0].post(route,data={'subject':'Ajuda privada','body':'Como acompanho meu pedido?'})
    assert response.status_code==303,response.text
    assert response.headers['location'].startswith(route+'?chamado=')
    tid=int(response.headers['location'].split('chamado=')[1])
    assert clients[0].get(route+'?chamado='+str(tid)).status_code==200
    assert clients[1].get('/p/'+b['slug']+'/suporte?chamado='+str(tid)).status_code==404
    with main.db() as c:
        main.nowup_admin205.notify(c,users[0],'Pode acompanhar nesta loja.',tid)
    with main.db() as c:
        notice=json.loads(c.execute('SELECT payload FROM customer_push112 WHERE user_id=? ORDER BY id DESC LIMIT 1',(users[0],)).fetchone()[0])
        assert notice['url']==route+'?chamado='+str(tid)


def test_foreground_alerts_use_store_scoped_session(setup345):
    import secrets
    main,(store,other),_=setup345
    token='alerts381-'+secrets.token_hex(12)
    with main.db() as c:
        uid=c.execute("INSERT INTO users(role,name,email,password_hash,email_verified,created_at,customer_store345,customer_email345) VALUES('customer','Avisos381',?,'unused',1,?,?,?)",('alerts381-'+token+'@example.invalid',main.now_iso(),store['id'],'alerts381@example.invalid')).lastrowid
        c.execute('INSERT INTO sessions(token,user_id,expires_at,store_id345) VALUES(?,?,?,?)',(token,uid,(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),store['id']))
        c.execute('INSERT INTO notifications(user_id,title,message,link,created_at) VALUES(?,?,?,?,?)',(uid,'Atualização do pedido','Aviso privado da loja','/p/'+store['slug']+'/pedidos',main.now_iso()))
    client=TestClient(main.app,headers={'Origin':'http://testserver'})
    client.cookies.set('nowup_loja345_'+str(store['id']),token,path='/p/'+store['slug'])
    assert client.get('/avisos203?after=0').status_code==401
    response=client.get('/p/'+store['slug']+'/avisos203?after=0')
    assert response.status_code==200
    assert any(n['message']=='Aviso privado da loja' for n in response.json()['notifications'])
    assert client.get('/p/'+other['slug']+'/avisos203?after=0').status_code==401
