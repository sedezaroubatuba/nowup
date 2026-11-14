from bs4 import BeautifulSoup
from test_checkout247 import checkout
from test_storeapp256 import shop
from test_storeapp257 import channel
from test_order_link377 import setup_order


def test_owner_can_advance_inside_order_buyer_cannot(channel, monkeypatch):
    m, client, result, order, item, owner, buyer = setup_order(channel)
    url=result['redirect']
    assert not BeautifulSoup(client.get(url).text,'html.parser').select('[data-status-form425]')
    monkeypatch.setattr(m,'current_user',lambda request:owner)
    endpoint='/painel/pedidos/'+str(order['id'])+'/status'
    with m.db() as c:
        c.execute("UPDATE orders SET payment_method='cash',status='confirmed',fulfillment_type='pickup' WHERE id=?",(order['id'],))
    for target in ['preparing','completed']:
        for page in [url,'/pedidos/'+str(order['id'])+'/notinha']:
            soup=BeautifulSoup(client.get(page).text,'html.parser')
            assert soup.select_one('[data-status-form425] button[value="'+target+'"]')
            assert not soup.select_one('[data-status-form425] button[value="out_for_delivery"]')
        response=client.post(endpoint,data={'status':target},headers={'Accept':'application/json'})
        assert response.status_code==200 and response.json()['status']==target
    assert not BeautifulSoup(client.get(url).text,'html.parser').select('[data-status-form425]')


def test_pix_guard_delivery_and_cancel_controls(channel, monkeypatch):
    m, client, result, order, item, owner, buyer=setup_order(channel)
    monkeypatch.setattr(m,'current_user',lambda request:owner)
    with m.db() as c:
        c.execute("UPDATE orders SET status='confirmed',fulfillment_type='delivery' WHERE id=?",(order['id'],))
    soup=BeautifulSoup(client.get(result['redirect']).text,'html.parser')
    assert not soup.select_one('[data-status-form425] button[value="preparing"]')
    assert soup.select_one('[data-status-form425] input[name="reason"][required]')
    endpoint='/painel/pedidos/'+str(order['id'])+'/status'
    assert client.post(endpoint,data={'status':'preparing'},headers={'Accept':'application/json'}).status_code==409
    with m.db() as c:
        c.execute("UPDATE orders SET payment_method='cash',status='preparing' WHERE id=?",(order['id'],))
    assert BeautifulSoup(client.get(result['redirect']).text,'html.parser').select_one('[data-status-form425] button[value="out_for_delivery"]')
    assert client.post(endpoint,data={'status':'cancelled','reason':'Cliente desistiu'},headers={'Accept':'application/json'}).status_code==200
    assert not BeautifulSoup(client.get(result['redirect']).text,'html.parser').select('[data-status-form425]')
