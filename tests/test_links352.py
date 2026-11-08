import pytest
from fastapi import HTTPException
from nowup_links352 import clean_url
from test_storeapp257 import channel
from test_storeapp256 import shop
from test_checkout247 import checkout


@pytest.mark.parametrize('url', ['javascript:alert(1)', 'http://site.example', 'https://user:pass@site.example', 'https://site.example\\@evil.example', 'https://site.example\n/'])
def test_invalid_links_are_rejected(url):
    with pytest.raises(HTTPException):clean_url(url)


def test_instagram_requires_its_own_domain():
    assert clean_url('https://www.instagram.com/sedezero', True).endswith('/sedezero')
    with pytest.raises(HTTPException):clean_url('https://instagram.com.evil.example/sedezero', True)


@pytest.mark.parametrize('plan,allowed', [('cardapio',True),('ambos',False),('completo',True)])
def test_plan_entitlements_cannot_be_bypassed_with_direct_urls(channel,monkeypatch,plan,allowed):
    m,client,slug,pid,data,product,customer=channel
    with m.db() as c:
        c.execute('UPDATE professionals SET plan_active=?,instagram_url=?,website_url=? WHERE id=?',(plan,'https://www.instagram.com/sedezero','https://example.com',pid))
        owner=dict(c.execute('SELECT u.* FROM users u JOIN professionals p ON p.user_id=u.id WHERE p.id=?',(pid,)).fetchone())
    for suffix in ('?loja=1','?origem=externo'):
        page=client.get('/p/'+slug+'/menu'+suffix)
        assert page.status_code==200
        assert ('"whatsappCheckout": true' in page.text)==allowed
        assert ('>Instagram</a>' in page.text)==allowed
        assert ('>Site</a>' in page.text)==allowed
    external=client.get('/p/'+slug+'/social/site',follow_redirects=False)
    assert external.status_code==(303 if allowed else 404)
    if allowed:assert external.headers['location']=='https://example.com'
    result=client.post('/p/'+slug+'/menu/whatsapp',data=data)
    assert result.status_code==(200 if allowed else 404)
    if allowed:
        assert result.json()['mode']=='whatsapp' and result.json()['recorded']
        assert result.json()['whatsapp_url'].startswith('https://wa.me/')
    else:
        with m.db() as c:assert c.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==0
    monkeypatch.setattr(m,'current_user',lambda request:owner)
    m.nowup_sales107.initialize()
    panel=client.get('/painel');assert panel.status_code==200
    assert ('id="cardapio-independente"' in panel.text)==allowed
    saved=client.post('/painel/cardapio/links352',data={'instagram_url':'https://instagram.com/minhaloja','website_url':'https://minhaloja.example'},follow_redirects=False)
    assert saved.status_code==(303 if allowed else 403)
    saved=client.post('/painel/cardapio/whatsapp',data={'mode':'whatsapp','whatsapp':'12999999999'},follow_redirects=False)
    assert saved.status_code==(303 if allowed else 403)


def test_complete_appears_in_showcase_but_standalone_does_not(shop):
    m,client,slug,pid,*_=shop
    with m.db() as c:
        category=c.execute('SELECT id FROM categories WHERE active=1 LIMIT 1').fetchone()[0]
        c.execute('INSERT OR IGNORE INTO professional_categories(professional_id,category_id) VALUES(?,?)',(pid,category))
        for plan,visible in [('cardapio',False),('ambos',True),('completo',True)]:
            c.execute('UPDATE professionals SET plan_active=? WHERE id=?',(plan,pid))
            assert bool(c.execute('SELECT p.id FROM professionals p WHERE p.id=? AND '+m.public_business_scope(),(pid,)).fetchone())==visible


def test_requested_upgrade_is_targeted_and_does_not_rewrite_payments(shop):
    import json
    import nowup_admin227 as adm
    from nowup_upgrade352 import upgrade_sede_zero
    m,client,slug,pid,*_=shop
    adm.configure(vars(m));adm.initialize()
    with m.db() as c:
        assert not upgrade_sede_zero(c)
        c.execute("UPDATE professionals SET slug='samuel-dos-santos-silva',display_name='ADEGA SEDE ZERO',is_demo=0 WHERE id=?",(pid,))
        c.execute("INSERT INTO adm227_entities(kind,id,data) VALUES('storemeta',?,?)",(pid,json.dumps({'price':9990,'method':'Pix'})))
        before=[tuple(row) for row in c.execute('SELECT * FROM products')]
        other=[tuple(row) for row in c.execute('SELECT * FROM professionals WHERE id<>?',(pid,))]
        assert upgrade_sede_zero(c)
        assert c.execute('SELECT plan_active FROM professionals WHERE id=?',(pid,)).fetchone()[0]=='completo'
        assert c.execute('SELECT mode FROM store_menu257 WHERE professional_id=?',(pid,)).fetchone()[0]=='whatsapp'
        meta=json.loads(c.execute("SELECT data FROM adm227_entities WHERE kind='storemeta' AND id=?",(pid,)).fetchone()[0])
        assert meta=={'price':9990,'method':'Pix','plan':'completo'}
        assert [tuple(row) for row in c.execute('SELECT * FROM products')]==before
        assert [tuple(row) for row in c.execute('SELECT * FROM professionals WHERE id<>?',(pid,))]==other
        c.execute("UPDATE professionals SET plan_active='cardapio' WHERE id=?",(pid,))
        assert not upgrade_sede_zero(c)
        assert c.execute('SELECT plan_active FROM professionals WHERE id=?',(pid,)).fetchone()[0]=='cardapio'
