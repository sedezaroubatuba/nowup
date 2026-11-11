from bs4 import BeautifulSoup
from test_checkout247 import checkout
from test_storeapp256 import shop
from test_storeapp257 import channel
from test_order_link377 import setup_order


def test_notice_has_items_and_acceptance_returns_details_without_redirect(channel,monkeypatch):
    m,client,result,o,item,owner,buyer=setup_order(channel)
    with m.db() as c:
        m.nowup_notinha401.initialize(c)
        c.execute("UPDATE orders SET order_origin='legacy' WHERE id=?",(o['id'],))
        c.execute("UPDATE order_items SET product_name=? WHERE id=?",('<img src=x onerror=alert(1)>',item['id']))
    monkeypatch.setattr(m,'current_user',lambda request:owner)
    data=client.get('/painel/pedidos/novos').json()
    assert data['pending_order']['id']==o['id']
    assert data['pending_order']['total_cents']==300
    assert data['pending_order']['items'][0]['quantity']==1
    fragment='/painel/pedidos/'+str(o['id'])+'/detalhes407'
    before=client.get(fragment)
    assert before.status_code==200 and '<html' not in before.text
    assert '&lt;img' in before.text and '<img src=x' not in before.text
    headers={'Accept':'application/json','X-NowUp-Order-Detail':'1'}
    response=client.post('/painel/pedidos/'+str(o['id'])+'/status',data={'status':'confirmed'},headers=headers,follow_redirects=False)
    assert response.status_code==200 and 'location' not in response.headers
    data=response.json();assert data['status']=='confirmed'
    page=BeautifulSoup(data['html407'],'html.parser')
    assert page.select_one('[data-order-status407="confirmed"]')
    assert page.select_one('.nu407-total strong').text=='R$ 3,00'
    assert 'Confirmar Pix recebido' in data['html407']
    with m.db() as c:assert not m.nowup_notinha401.payment_checked(c,dict(o))
    again=client.post('/painel/pedidos/'+str(o['id'])+'/status',data={'status':'confirmed'},headers=headers,follow_redirects=False)
    assert again.status_code==200 and again.json()['html407']
    assert client.get('/painel/pedidos/novos').json()['pending_count']==0
    monkeypatch.setattr(m,'current_user',lambda request:buyer)
    assert client.get(fragment).status_code==403
    monkeypatch.setattr(m,'current_user',lambda request:dict(owner,id=999999))
    assert client.get(fragment).status_code==404
