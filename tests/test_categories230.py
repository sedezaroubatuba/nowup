"""Category persistence, tenant isolation and safe automatic icon matching."""
import importlib
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nowup_categories230 import resolve, icon, validate_key

@pytest.mark.parametrize('name,key', [('Cervejas','beer'),('Cervejas fardos ou six pack','pack'),('Água','water'),('Sedas','paper'),('Tabacos','leaf'),('Cigarros','cigarette'),('Balas/doces e chicletes','candy'),('Chocolates','chocolate'),('Bebidas alcoólicas mistas','cocktail'),('Destilados','bottle'),('Farmácias','medicine'),('Uma categoria nova e desconhecida','grid')])
def test_names(name,key):
    assert resolve(name)==key

def test_manual_and_untrusted_values():
    assert resolve('Cervejas','pizza')=='pizza'
    assert validate_key('<script>bad</script>')=='auto'
    assert '<script' not in str(icon('<script>alert(1)</script>','<img onerror=bad>'))

@pytest.fixture(scope='module')
def env(tmp_path_factory):
    directory=tmp_path_factory.mktemp('categories230')
    os.environ['NOWUP_DB']=str(directory/'test.db')
    os.environ['NOWUP_UPLOAD_DIR']=str(directory/'uploads')
    os.environ['NOWUP_ADMIN_EMAIL']='admin@test.invalid'
    os.environ['NOWUP_ADMIN_PASSWORD']='isolated-local-test-password'
    m=importlib.import_module('app')
    for callback in m.app.router.on_startup:
        if callback.__name__!='start': callback()
    with m.db() as c:
        stores=c.execute('SELECT id,user_id,slug FROM professionals ORDER BY id LIMIT 2').fetchall()
        for idx,p in enumerate(stores):
            c.execute("UPDATE professionals SET offer_mode='menu',is_premium=1,plan_active='ambos' WHERE id=?",(p['id'],))
            c.execute('INSERT INTO sessions(token,user_id,expires_at) VALUES(?,?,?)',(f'icon-test-{idx}',p['user_id'],(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()))
        c.commit()
    client=TestClient(m.app,headers={'Origin':'http://testserver'}); client.cookies.set('nowup_session','icon-test-0')
    return m,client,stores

def test_save_rename_and_tenant_boundary(env):
    m,client,stores=env; pid=stores[0]['id']
    response=client.post('/painel/cardapio/categorias',data={'name':'Ícone teste','icon_key':'pizza'},follow_redirects=False)
    assert response.status_code==303
    with m.db() as c: row=c.execute('SELECT * FROM product_categories WHERE professional_id=? AND name=?',(pid,'Ícone teste')).fetchone()
    assert row['icon_key']=='pizza'
    client.cookies.set('nowup_session','icon-test-1')
    client.post(f"/painel/cardapio/categorias/{row['id']}",data={'name':'Invasão','icon_key':'beer','active':'1'},follow_redirects=False)
    with m.db() as c: assert c.execute('SELECT icon_key FROM product_categories WHERE id=?',(row['id'],)).fetchone()[0]=='pizza'
    client.cookies.set('nowup_session','icon-test-0')
    client.post(f"/painel/cardapio/categorias/{row['id']}",data={'name':'Renomeada','active':'1'},follow_redirects=False)
    with m.db() as c:
        saved=c.execute('SELECT * FROM product_categories WHERE id=?',(row['id'],)).fetchone()
        assert saved['name']=='Renomeada' and saved['icon_key']=='pizza'
    client.post(f"/painel/cardapio/categorias/{row['id']}",data={'name':'Água','icon_key':'auto','active':'1'},follow_redirects=False)
    with m.db() as c: assert c.execute('SELECT icon_key FROM product_categories WHERE id=?',(row['id'],)).fetchone()[0]=='auto'

def test_rendered_pages_and_migration(env):
    m,client,stores=env
    m.init_db() # migration must remain idempotent on existing database
    for path in ['/', '/painel', '/p/'+stores[0]['slug'], '/p/'+stores[0]['slug']+'/menu']:
        response=client.get(path)
        assert response.status_code==200, (path,response.text[:200])
        assert 'nu230-data' in response.text
        assert 'categories230.js' in response.text
    assert 'data-icon-picker230' in client.get('/painel').text


def test_carousel_preference_is_persistent_validated_and_store_specific(env):
    m,client,stores=env
    client.cookies.set('nowup_session','icon-test-0')
    with m.db() as c:
        other_before=c.execute('SELECT carousel_layout235 FROM professionals WHERE id=?',(stores[1]['id'],)).fetchone()[0]
    response=client.post('/painel/cardapio/exibicao',data={'carousel_layout235':'large'},follow_redirects=False)
    assert response.status_code==303
    with m.db() as c:
        assert c.execute('SELECT carousel_layout235 FROM professionals WHERE id=?',(stores[0]['id'],)).fetchone()[0]=='large'
        assert c.execute('SELECT carousel_layout235 FROM professionals WHERE id=?',(stores[1]['id'],)).fetchone()[0]==other_before
    assert 'data-carousel-layout="large"' in client.get('/p/'+stores[0]['slug']).text
    assert 'Foto grande — 1 produto por vez' in client.get('/painel').text
    assert client.post('/painel/cardapio/exibicao',data={'carousel_layout235':'invalid'},follow_redirects=False).status_code==422
    with m.db() as c:
        assert c.execute('SELECT carousel_layout235 FROM professionals WHERE id=?',(stores[0]['id'],)).fetchone()[0]=='large'
    assert client.post('/painel/cardapio/exibicao',data={'carousel_layout235':'compact'},follow_redirects=False).status_code==303
    assert 'data-carousel-layout="compact"' in client.get('/p/'+stores[0]['slug']).text


def test_two_product_carousel_setting(env):
    m,client,stores=env
    client.cookies.set('nowup_session','icon-test-0')
    assert client.post('/painel/cardapio/exibicao',data={'carousel_layout235':'pair'},follow_redirects=False).status_code==303
    for suffix in ['', '/menu']:
        assert 'data-carousel-layout="pair"' in client.get('/p/'+stores[0]['slug']+suffix).text
    panel=client.get('/painel').text
    assert "value=\"pair\" checked" in panel
    assert "value=\"compact\" checked" not in panel
    with m.db() as c:
        assert c.execute('SELECT carousel_layout235 FROM professionals WHERE id=?',(stores[0]['id'],)).fetchone()[0]=='pair'


def test_mutations_reject_missing_and_cross_origin_and_webhook_keeps_own_auth(env):
    _,client,_=env
    client.headers.pop('Origin',None)
    try:
        for headers in [{},{'Origin':'null'},{'Origin':'https://evil.invalid'}]:
            assert client.post('/painel/cardapio/exibicao',data={'carousel_layout235':'pair'},headers=headers).status_code==403
        assert client.post('/painel/cardapio/exibicao',data={'carousel_layout235':'pair'},headers={'Referer':'http://testserver/painel'},follow_redirects=False).status_code==303
        assert client.post('/integracoes/asaas/webhook',json={}).status_code==404  # Integration is not enabled in this app.
    finally:client.headers['Origin']='http://testserver'


def test_store_pagination_preserves_filters_and_reaches_all_results(env):
    m,client,_=env;stamp=datetime.now(timezone.utc).isoformat()
    with m.db() as c:
        category=c.execute('SELECT id FROM categories WHERE active=1 LIMIT 1').fetchone()[0]
        for n in range(27):
            uid=c.execute("INSERT INTO users(role,name,email,password_hash,created_at) VALUES('professional',?,?,?,?)",(f'Paging238 {n}',f'paging238-{n}@test.invalid','unused',stamp)).lastrowid
            pid=c.execute("INSERT INTO professionals(user_id,slug,display_name,city,created_at,plan_active,admission_status) VALUES(?,?,?,?,?,'ambos','approved')",(uid,f'paging238-{n}',f'Paging238 {n}','Ubatuba',stamp)).lastrowid
            c.execute('INSERT INTO professional_categories VALUES(?,?)',(pid,category))
        c.commit()
    import re
    first=client.get('/profissionais?q=Paging238&city=Ubatuba').text
    second=client.get('/profissionais?q=Paging238&city=Ubatuba&page=2').text
    a=set(re.findall(r'href="/p/(paging238-\d+)"',first));b=set(re.findall(r'href="/p/(paging238-\d+)"',second))
    assert len(a)==24 and len(b)==3 and not a&b
    assert 'Mais lojas' in first and 'Mais lojas' not in second
    assert 'q=Paging238' in first and 'page=2' in first
    home=client.get('/?q=Paging238&city=Ubatuba').text
    assert 'Continuar vendo lojas' in home and '(27)' in home
