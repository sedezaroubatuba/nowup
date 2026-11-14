from test_checkout247 import checkout
from test_storeapp256 import shop
from test_storeapp257 import channel
from test_order_link377 import setup_order

def test_cardapio_pending_alert_is_global_private_and_stops_on_accept(channel,monkeypatch):
    m,client,result,o,item,owner,buyer=setup_order(channel)
    m.nowup_sales107.initialize()
    monkeypatch.setattr(m,'current_user',lambda r:owner)
    data=client.get('/painel/pedidos/novos').json()
    assert data['pending_count']==1 and data['pending_order']['id']==o['id']
    assert data['pending_order']['items'][0]['product_name']=='Auditoria'
    for path in ['/painel','/painel/cardapio/pedidos',result['redirect']+'?lojista=1']:
        page=client.get(path);assert page.status_code==200,(path,page.text[:100])
        assert 'data-order-alerts' in page.text,path
    assert client.post('/painel/pedidos/'+str(o['id'])+'/status',data={'status':'confirmed'},headers={'Accept':'application/json'}).status_code==200
    assert client.get('/painel/pedidos/novos').json()['pending_count']==0
    monkeypatch.setattr(m,'current_user',lambda r:dict(owner,id=999999))
    # Another real store's owner cannot see this order.
    with m.db() as c:
        other=c.execute('SELECT u.* FROM users u JOIN professionals p ON p.user_id=u.id WHERE p.id!=? LIMIT 1',(o['professional_id'],)).fetchone()
    if other:
        monkeypatch.setattr(m,'current_user',lambda r:dict(other))
        assert client.get('/painel/pedidos/novos').json()['pending_count']==0
    monkeypatch.setattr(m,'current_user',lambda r:buyer)
    assert client.get('/painel/pedidos/novos').status_code==403
