from bs4 import BeautifulSoup
from test_checkout247 import checkout
from test_storeapp256 import shop
from test_storeapp257 import channel

def test_customer_cardapio_has_no_merchant_entry(channel,monkeypatch):
    m,client,slug,pid,data,product,customer=channel
    monkeypatch.setattr(m,'current_user',lambda request:None)
    for path in ['/p/'+slug+'/entrar','/p/'+slug+'/cardapio']:
        r=client.get(path);assert r.status_code==200
        soup=BeautifulSoup(r.text,'html.parser')
        assert not soup.select('[data-store-merchant405]')
        assert not soup.select('a[href="/entrar?tipo=profissional"]')
    soup=BeautifulSoup(client.get('/entrar?tipo=profissional').text,'html.parser')
    assert not soup.select('a[href="/entrar?tipo=cliente"],a[href="/cadastro/cliente"]')
    assert soup.select_one('input[name=tipo][value=profissional]')

def test_owner_can_still_view_own_cardapio(channel,monkeypatch):
    m,client,slug,pid,data,product,customer=channel
    with m.db() as c:
        owner=dict(c.execute('SELECT u.* FROM users u JOIN professionals p ON p.user_id=u.id WHERE p.id=?',(pid,)).fetchone())
    monkeypatch.setattr(m,'current_user',lambda request:owner)
    r=client.get('/p/'+slug+'/cardapio')
    assert r.status_code==200
    assert 'Auditoria' in r.text
