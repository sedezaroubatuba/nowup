from bs4 import BeautifulSoup
from test_checkout247 import checkout
from test_storeapp256 import shop
from test_storeapp257 import channel
from test_order_link377 import setup_order
from test_runtime238 import request
from nowup_runtime238 import mutation_origin_allowed


def test_payment_confirmation_replaces_customer_qr_and_invalidates_after_total_change(channel, monkeypatch):
    m, client, result, order, item, owner, buyer = setup_order(channel)
    with m.db() as c:
        m.nowup_notinha401.initialize(c)
    path='/pedido/'+order['tracking_token']
    assert client.get(path+'/status').json()['payment_confirmed'] is False
    monkeypatch.setattr(m,'current_user',lambda request:owner)
    response=client.post('/painel/pedidos/'+str(order['id'])+'/status',data={'status':'confirmed'},headers={'Accept':'application/json'},follow_redirects=False)
    assert response.status_code==200 and response.json()['status']=='confirmed'
    assert client.get(path+'/status').json()['payment_confirmed'] is False
    assert client.post('/painel/pedidos/'+str(order['id'])+'/conferir-pix',follow_redirects=False).status_code==303
    monkeypatch.setattr(m,'current_user',lambda request:buyer)
    assert client.get(path+'/status').json()['payment_confirmed'] is True
    page=BeautifulSoup(client.get(path).text,'html.parser')
    assert page.select_one('[data-pix-confirmed405]')
    assert not page.select_one('[data-pix-payment]')
    with m.db() as c:c.execute('UPDATE orders SET total_cents=total_cents+100 WHERE id=?',(order['id'],))
    assert client.get(path+'/status').json()['payment_confirmed'] is False
    assert not BeautifulSoup(client.get(path).text,'html.parser').select_one('[data-pix-confirmed405]')


def test_custom_domain_requires_browser_same_origin_metadata(monkeypatch):
    monkeypatch.setenv('NOWUP_HTTPS','1')
    monkeypatch.setenv('NOWUP_PUBLIC_ORIGIN','https://canonical.example')
    assert mutation_origin_allowed(request({'origin':'https://testserver','sec-fetch-site':'same-origin'}))
    assert not mutation_origin_allowed(request({'origin':'https://testserver','sec-fetch-site':'cross-site'}))
    assert not mutation_origin_allowed(request({'origin':'https://evil.example','sec-fetch-site':'same-origin'}))
