import pytest
from fastapi.testclient import TestClient
from test_checkout247 import checkout
from test_storeapp256 import shop
from test_storeapp257 import channel
from nowup_menu_origin355 import menu_origin, external_menu


@pytest.fixture
def dedicated(channel, monkeypatch):
    m, old, slug, pid, data, product, customer = channel
    import cms
    monkeypatch.setattr(cms,'db',m.db)
    monkeypatch.setenv('NOWUP_MENU_ORIGIN', 'https://menu.example.com')
    monkeypatch.setenv('NOWUP_PUBLIC_ORIGIN', 'http://testserver')
    client = TestClient(m.app, base_url='https://menu.example.com',
                        headers={'Origin': 'https://menu.example.com'}, follow_redirects=False)
    return m, old, client, slug, pid, data


def test_unconfigured_links_keep_current_host(shop, monkeypatch):
    monkeypatch.delenv('NOWUP_MENU_ORIGIN', raising=False)
    _, client, slug, *_ = shop
    r = client.get('/p/' + slug + '/menu?loja=1', follow_redirects=False)
    assert r.status_code == 200
    assert 'store-app256' in r.text


def test_external_navigation_redirects_but_marketplace_stays(dedicated):
    m, old, new, slug, pid, data = dedicated
    path = '/p/' + slug + '/menu'
    for query in ('?loja=1', '?origem=externo'):
        r = old.get(path + query, follow_redirects=False)
        assert r.status_code == 307
        assert r.headers['location'] == 'https://menu.example.com' + path + query
    r = old.get(path, follow_redirects=False)
    assert r.status_code == 200 and 'id="store-app256"' not in r.text
    assert new.get(path).status_code == 200
    assert 'id="store-app256"' in new.get(path).text
    with m.db() as c:
        c.execute("UPDATE professionals SET plan_active='cardapio' WHERE id=?", (pid,))
    assert old.get(path, follow_redirects=False).status_code == 307


def test_menu_origin_cannot_open_or_install_marketplace(dedicated):
    _, _, client, slug, *_ = dedicated
    for path in ('/', '/app', '/painel', '/cliente', '/static/nowup.webmanifest', '/static/nowup-lojista.webmanifest'):
        assert client.get(path).status_code == 404
    base = '/p/' + slug + '/'
    manifest = client.get(base + 'manifest.webmanifest')
    assert manifest.status_code == 200
    assert manifest.json()['scope'] == base
    worker = client.get(base + 'service-worker355.js')
    assert worker.status_code == 200
    assert worker.headers['service-worker-allowed'] == base
    assert 'const STORE_SCOPE="' + base + '"' in worker.text
    for tail in ('termos', 'privacidade'):
        r = client.get(base + tail)
        assert r.status_code == 200 and 'id="store-app256"' in r.text
    assert client.get('/p/nonexistent/manifest.webmanifest').status_code == 404


def test_whatsapp_checkout_accepts_only_its_own_origin(dedicated):
    m, old, client, slug, pid, data = dedicated
    path = '/p/' + slug + '/menu/whatsapp'
    for origin in ('http://testserver', 'https://evil.example.com'):
        assert client.post(path, data=data, headers={'Origin': origin}).status_code == 403
    r = client.post(path, data=data)
    assert r.status_code == 200, r.text
    assert r.json()['whatsapp_url'].startswith('https://wa.me/5512999999999?text=')
    assert r.json()['prepared'] and r.json()['recorded']
    with m.db() as c:
        assert c.execute('SELECT COUNT(*) FROM orders').fetchone()[0] == 1
        assert c.execute('SELECT status FROM orders').fetchone()[0] == 'awaiting_payment'
    # Configuration must not redirect or replay a POST on an old link.
    assert old.post(path, data=data, follow_redirects=False).status_code == 200


def test_store_emails_and_panel_links_use_dedicated_origin(dedicated, monkeypatch):
    m, old, client, slug, pid, _ = dedicated
    from nowup_storeaccounts345 import send_confirmation
    sent = []
    monkeypatch.setattr(m, 'send_email', lambda *a: sent.append(a) or True)
    p = {'id': pid, 'slug': slug, 'display_name': 'Sede Zero'}
    assert send_confirmation(vars(m), p, 'Cliente', 'mail@example.com', 'token')
    assert 'https://menu.example.com/p/' + slug + '/verificar-email?token=token' in sent[-1][3]
    from starlette.requests import Request
    req = Request({'type': 'http', 'scheme': 'http', 'path': '/', 'headers': [(b'host', b'testserver')], 'query_string': b''})
    assert external_menu(req, slug) == 'https://menu.example.com/p/' + slug + '/cardapio'


def test_merchant_panel_advertises_external_links_only_for_entitled_plans(dedicated, monkeypatch):
    m, old, _, slug, pid, _ = dedicated
    for callback in m.app.router.on_startup:
        if callback.__name__ != 'start':
            callback()
    with m.db() as c:
        owner = dict(c.execute('SELECT u.* FROM users u JOIN professionals p ON p.user_id=u.id WHERE p.id=?', (pid,)).fetchone())
    monkeypatch.setattr(m, 'current_user', lambda request: owner)
    r = old.get('/painel')
    assert r.status_code == 200, r.text
    assert 'data-profile-url="https://menu.example.com/p/' + slug + '/cardapio"' in r.text
    with m.db() as c:
        c.execute("UPDATE professionals SET plan_active='ambos' WHERE id=?", (pid,))
    r = old.get('/painel')
    assert r.status_code == 200
    assert 'href="/p/' + slug + '/menu">Ver cardápio público' in r.text
    assert 'data-profile-url="https://menu.example.com/' not in r.text


@pytest.mark.parametrize('value', ['http://menu.example.com', 'https://evil.example.com/path',
                                  'https://user:pass@menu.example.com', 'https://menu.example.com?x=1',
                                  'https://menu.example.com#fragment', 'https://menu.example.com:bad',
                                  'https://menu.example.com\\evil'])
def test_invalid_configuration_fails_closed(monkeypatch, value):
    monkeypatch.setenv('NOWUP_MENU_ORIGIN', value)
    with pytest.raises(ValueError):
        menu_origin()


def test_same_origin_is_rejected(monkeypatch):
    monkeypatch.setenv('NOWUP_PUBLIC_ORIGIN', 'https://app.example.com')
    monkeypatch.setenv('NOWUP_MENU_ORIGIN', 'https://app.example.com')
    with pytest.raises(ValueError):
        menu_origin()
