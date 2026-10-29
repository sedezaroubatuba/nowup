import io,json
import pytest
from PIL import Image
from test_checkout247 import checkout

@pytest.fixture
def shop(checkout,monkeypatch):
    m,client,url,data,pid,customer=checkout
    with m.db() as c:
        p=c.execute('SELECT p.* FROM professionals p JOIN products pr ON pr.professional_id=p.id WHERE pr.id=?',(pid,)).fetchone();slug=p['slug']
        c.execute("UPDATE professionals SET display_name='Sede Zero',avatar_filename='' WHERE id=?",(p['id'],))
    m.nowup_home210.configure(vars(m))
    return m,client,slug,p['id'],url,data,pid

def test_manifest_identity_and_scope_are_per_store(shop):
    m,client,slug,pid,*_=shop
    a=client.get('/p/'+slug+'/manifest.webmanifest');assert a.status_code==200,a.text
    data=a.json();assert data['name']=='Sede Zero'
    assert data['scope']=='/p/'+slug+'/' and data['start_url'].startswith(data['scope'])
    assert data['id']!='/app' and data['id'].startswith(data['scope'])
    with m.db() as c:
        other=c.execute('SELECT id,slug FROM professionals WHERE id<>? LIMIT 1',(pid,)).fetchone()
        c.execute("UPDATE professionals SET plan_active='cardapio',is_premium=1,offer_mode='menu',admission_status='approved',blocked=0 WHERE id=?",(other['id'],))
    b=client.get('/p/'+other['slug']+'/manifest.webmanifest');assert b.status_code==200
    assert b.json()['id']!=data['id'] and b.json()['scope']!=data['scope']
    assert a.headers['cache-control']=='private, no-store'

@pytest.mark.parametrize('condition',['blocked','pending','vitrine','owner_disabled'])
def test_manifest_respects_publication_and_plan(shop,condition):
    m,client,slug,pid,*_=shop
    with m.db() as c:
        if condition=='blocked':c.execute('UPDATE professionals SET blocked=1 WHERE id=?',(pid,))
        elif condition=='pending':c.execute("UPDATE professionals SET admission_status='pending' WHERE id=?",(pid,))
        elif condition=='vitrine':c.execute("UPDATE professionals SET plan_active='vitrine' WHERE id=?",(pid,))
        else:c.execute('UPDATE users SET is_active=0 WHERE id=(SELECT user_id FROM professionals WHERE id=?)',(pid,))
    assert client.get('/p/'+slug+'/manifest.webmanifest').status_code==404
    assert client.get('/p/'+slug+'/app-icon/192.png').status_code==404

@pytest.mark.parametrize('size',[192,512])
def test_icons_use_store_logo_and_fallback(shop,size):
    m,client,slug,pid,*_=shop
    result=client.get(f'/p/{slug}/app-icon/{size}.png');assert result.status_code==200
    with Image.open(io.BytesIO(result.content)) as im:assert im.size==(size,size)
    Image.new('RGB',(50,30),'red').save(m.UPLOAD_DIR/'logo256.png')
    with m.db() as c:c.execute("UPDATE professionals SET avatar_filename='logo256.png' WHERE id=?",(pid,))
    logo=client.get(f'/p/{slug}/app-icon/{size}.png')
    with Image.open(io.BytesIO(logo.content)) as im:assert im.getpixel((size//2,size//2))==(255,0,0)
    assert client.get(f'/p/{slug}/app-icon/1024.png').status_code==404


def test_explicit_store_link_and_cardapio_only_show_store_brand(shop):
    m,client,slug,pid,*_=shop
    plain=client.get('/p/'+slug+'/menu');assert plain.status_code==200,plain.text
    assert 'id="store-app256"' not in plain.text
    own=client.get('/p/'+slug+'/menu?loja=1');assert own.status_code==200,own.text
    assert 'id="store-app256"' in own.text and 'Instalar loja' in own.text
    assert 'href="/p/'+slug+'/manifest.webmanifest"' in own.text
    with m.db() as c:c.execute("UPDATE professionals SET plan_active='cardapio' WHERE id=?",(pid,))
    auto=client.get('/p/'+slug+'/menu');assert 'id="store-app256"' in auto.text
    assert 'id="store-app256"' not in client.get('/entrar').text


def test_scoped_checkout_stays_idempotent_and_tracks_only_its_store(shop):
    m,client,slug,pid,url,data,_=shop
    headers={'Accept':'application/json','X-Nowup-Store-App':'256'}
    first=client.post(url,data=data,headers=headers);assert first.status_code==200,first.text
    target=first.json()['redirect'];assert target.startswith('/p/'+slug+'/pedido/')
    assert client.post(url,data=data,headers=headers).json()['redirect']==target
    tracking=client.get(target);assert tracking.status_code==200,tracking.text
    assert 'id="store-app256"' in tracking.text and 'Sede Zero' in tracking.text
    with m.db() as c:
        assert c.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==1
        other=c.execute('SELECT slug FROM professionals WHERE id<>? LIMIT 1',(pid,)).fetchone()[0]
    assert client.get('/p/'+other+'/pedido/'+target.rsplit('/',1)[1]).status_code==404


def test_store_login_reuses_customer_auth_and_safe_return(shop,monkeypatch):
    import admin_customization
    from fastapi.responses import RedirectResponse
    m,client,slug,*_=shop
    page=client.get('/p/'+slug+'/entrar?tipo=cliente');assert page.status_code==200
    assert 'action="/p/'+slug+'/entrar?tipo=cliente"' in page.text
    calls=[]
    def login(request,email,password,tipo):
        calls.append(tipo);r=RedirectResponse('/',303);r.set_cookie('nowup_session','isolated');return r
    monkeypatch.setattr(admin_customization,'secure_login',login)
    result=client.post('/p/'+slug+'/entrar',data={'email':'test@example.invalid','password':'unused'},follow_redirects=False)
    assert calls==['cliente'] and result.headers['location']=='/p/'+slug+'/menu?loja=1'
    assert 'nowup_session=' in result.headers['set-cookie']
    assert client.post('/p/not-a-store/entrar',data={'email':'test@example.invalid','password':'unused'},follow_redirects=False).status_code==404


def test_signup_context_is_optional_and_does_not_allow_external_redirects(shop):
    m,client,slug,*_=shop
    result=client.get('/cadastro/cliente?loja='+slug);assert result.status_code==200
    assert 'id="store-app256"' in result.text
    assert 'nowup_store_return256=' in result.headers.get('set-cookie','')
    client.cookies.clear()
    bad=client.get('/cadastro/cliente?loja=https://evil.invalid');assert bad.status_code==200
    assert 'id="store-app256"' not in bad.text


def test_real_customer_login_returns_to_store_and_preserves_session(shop,monkeypatch):
    import admin_customization
    m,client,slug,*_=shop
    monkeypatch.setattr(admin_customization,'db',m.db)
    with m.db() as c:
        c.execute("UPDATE users SET password_hash=?,email_verified=1 WHERE email='audit247@example.invalid'",(m.hash_password('storeapp-test-password'),))
    response=client.post('/p/'+slug+'/entrar',data={'email':'audit247@example.invalid','password':'storeapp-test-password'},follow_redirects=False)
    assert response.status_code==303 and response.headers['location']=='/p/'+slug+'/menu?loja=1'
    assert 'nowup_session=' in response.headers['set-cookie']
    bad=client.post('/p/'+slug+'/entrar',data={'email':'audit247@example.invalid','password':'wrong'},follow_redirects=False)
    assert bad.headers['location'].startswith('/p/'+slug+'/entrar?erro=1')
