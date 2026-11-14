from datetime import datetime, timedelta, timezone
from urllib.parse import unquote
from bs4 import BeautifulSoup
from test_checkout247 import checkout
from test_storeapp256 import shop
from test_storeapp257 import channel
from test_order_link377 import setup_order
from nowup_wait434 import greeting, dynamic_greeting


def test_greetings_use_brasilia_and_replace_fixed_salutation():
    # 01:00 UTC is 22:00 in Ubatuba, including a UTC date boundary.
    night=datetime(2026,11,15,1,tzinfo=timezone.utc)
    assert greeting(night)=='boa noite'
    assert dynamic_greeting('Olá, boa tarde! Meu pedido.',night)=='Olá, boa noite! Meu pedido.'
    for hour,expected in [(3,'boa noite'),(5,'bom dia'),(11,'bom dia'),(12,'boa tarde'),(17,'boa tarde'),(18,'boa noite'),(22,'boa noite')]:
        assert greeting(datetime(2026,11,14,hour+3 if hour<21 else hour-21,tzinfo=timezone.utc))==expected


def test_countdown_handoff_same_order_and_blocks_merchant(channel,monkeypatch):
    m,client,result,o,item,owner,buyer=setup_order(channel)
    endpoint=result['redirect']+'/espera434'
    page=BeautifulSoup(client.get(result['redirect']).text,'html.parser')
    assert page.select_one('[data-wait434]')['data-endpoint434']==endpoint
    state=client.get(endpoint).json()
    assert state['status']=='new' and not state['eligible']
    assert client.post(endpoint).status_code==409
    old=(datetime.now(timezone.utc)-timedelta(seconds=61)).isoformat()
    with m.db() as c:c.execute('UPDATE orders SET created_at=? WHERE id=?',(old,o['id']))
    assert client.get(endpoint).json()['eligible']
    monkeypatch.setattr(m,'current_user',lambda r:dict(buyer,id=buyer['id']+10000))
    assert client.post(endpoint).status_code==404
    monkeypatch.setattr(m,'current_user',lambda r:owner)
    assert client.post(endpoint).status_code==403
    detail=client.get('/painel/pedidos/'+str(o['id'])+'/detalhes407')
    assert 'data-wait434' in detail.text
    monkeypatch.setattr(m,'current_user',lambda r:buyer)
    assert client.post(endpoint,headers={'Origin':'https://evil.invalid'}).status_code==403
    transfer=client.post(endpoint)
    assert transfer.status_code==200,transfer.text
    data=transfer.json()
    assert data['status']=='whatsapp_finalized'
    message=unquote(data['whatsapp_url'])
    assert o['order_code'] in message and item['product_name'] in message
    assert client.post(endpoint).json()['status']=='whatsapp_finalized'
    page=client.get(result['redirect'])
    assert 'data-pix-payment' not in page.text
    assert 'Pagamento bloqueado no NowUp' in page.text
    monkeypatch.setattr(m,'current_user',lambda r:owner)
    assert client.post('/painel/pedidos/'+str(o['id'])+'/status',data={'status':'confirmed'},headers={'Accept':'application/json'}).status_code==409
    assert client.post('/painel/pedidos/'+str(o['id'])+'/conferir-pix').status_code==409
    assert client.post('/painel/pedidos/'+str(o['id'])+'/revisao',data={'keep':str(item['id']),'qty_'+str(item['id']):'1','price_'+str(item['id']):'3.00'}).status_code==409
    with m.db() as c:
        assert c.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==1
        assert c.execute("SELECT COUNT(*) FROM order_status_history WHERE order_id=? AND status='whatsapp_finalized'",(o['id'],)).fetchone()[0]==1


def test_acceptance_wins_and_payment_stays_in_nowup(channel,monkeypatch):
    m,client,result,o,item,owner,buyer=setup_order(channel)
    old=(datetime.now(timezone.utc)-timedelta(seconds=61)).isoformat()
    with m.db() as c:c.execute('UPDATE orders SET created_at=? WHERE id=?',(old,o['id']))
    monkeypatch.setattr(m,'current_user',lambda r:owner)
    assert client.post('/painel/pedidos/'+str(o['id'])+'/status',data={'status':'confirmed'},follow_redirects=False).status_code==303
    monkeypatch.setattr(m,'current_user',lambda r:buyer)
    assert client.post(result['redirect']+'/espera434').status_code==409
    page=client.get(result['redirect'])
    assert 'Seu pedido foi aceito!' in page.text and 'data-pix-payment' in page.text
    assert 'data-wait434' not in page.text


def test_scheduled_order_countdown_starts_when_store_can_accept(channel):
    m,client,result,o,*_=setup_order(channel)
    future=datetime.now(timezone.utc)+timedelta(hours=2)
    with m.db() as c:c.execute('UPDATE orders SET accept_after380=? WHERE id=?',(future.isoformat(),o['id']))
    state=client.get(result['redirect']+'/espera434').json()
    assert datetime.fromisoformat(state['deadline'])==future+timedelta(seconds=60)
    assert not state['eligible']
