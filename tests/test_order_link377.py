"""Cardapio review, same-order chat and Pix release regressions."""
import json
import pytest
from bs4 import BeautifulSoup
from test_checkout247 import checkout
from test_storeapp256 import shop
from test_storeapp257 import channel
from test_pix import KEY, parse


def setup_order(channel):
    m,client,slug,pid,data,product,buyer=channel
    m.nowup_receipts206.initialize()
    with m.db() as c:
        c.execute('UPDATE professionals SET pix_key=?,pix_key_type=?,pix_receiver_name=?,pix_receiver_city=? WHERE id=?',(KEY,'random','Loja teste','Ubatuba',pid))
        owner=dict(c.execute('SELECT u.* FROM users u JOIN professionals p ON p.user_id=u.id WHERE p.id=?',(pid,)).fetchone())
    result=client.post('/p/'+slug+'/menu/whatsapp',data=data).json()
    with m.db() as c:
        order=dict(c.execute('SELECT * FROM orders').fetchone())
        item=dict(c.execute('SELECT * FROM order_items').fetchone())
    return m,client,result,order,item,owner,buyer


def test_full_review_changed_price_requires_buyer_acceptance(channel,monkeypatch):
    m,client,result,order,item,owner,buyer=setup_order(channel)
    assert result['pix'] and 'data-pix-payment' in client.get(result['redirect']).text
    monkeypatch.setattr(m,'current_user',lambda request:owner)
    page=client.get(result['redirect'])
    assert page.status_code==200 and 'Confirmar pedido' in page.text and 'Conversa' in page.text
    revision={'keep':str(item['id']),'qty_'+str(item['id']):'1','price_'+str(item['id']):'38.00','message':'Preço corrigido: confirma?'}
    assert client.post('/painel/pedidos/'+str(order['id'])+'/revisao',data=revision,follow_redirects=False).status_code==303
    with m.db() as c:
        r=dict(c.execute('SELECT * FROM order_revisions').fetchone())
        assert c.execute('SELECT total_cents FROM orders').fetchone()[0]==300
    assert 'data-pix-payment' not in client.get(result['redirect']).text
    # A different customer cannot accept, inspect the order or use its chat.
    monkeypatch.setattr(m,'current_user',lambda request:dict(buyer,id=buyer['id']+1000))
    endpoint='/p/'+channel[2]+'/pedido/'+order['tracking_token']+'/revisao/'+str(r['id'])
    assert client.post(endpoint,data={'decision':'accept'},follow_redirects=False).status_code==404
    assert client.get('/pedidos/'+str(order['id'])+'/conversa').status_code==403
    monkeypatch.setattr(m,'current_user',lambda request:buyer)
    assert client.post(endpoint,data={'decision':'accept'},follow_redirects=False).status_code==303
    # Duplicate acceptance cannot mutate an already confirmed order.
    assert client.post(endpoint,data={'decision':'accept'},follow_redirects=False).status_code==409
    after=client.get(result['redirect']);assert after.status_code==200
    script=BeautifulSoup(after.text,'html.parser').select_one('[data-pix-payment] script')
    assert parse(json.loads(script.string)['payload'])['54']=='38.00'
    assert client.post('/pedidos/'+str(order['id'])+'/conversa',data={'message':'Vou pagar agora.'}).status_code==200
    monkeypatch.setattr(m,'current_user',lambda request:owner)
    assert client.get('/pedidos/'+str(order['id'])+'/conversa').json()['messages'][0]['body']=='Vou pagar agora.'
    with m.db() as c:
        assert c.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==1
        assert c.execute('SELECT unit_price_cents FROM order_items').fetchone()[0]==3800
        assert c.execute('SELECT status FROM orders').fetchone()[0]=='confirmed'


def test_no_change_confirmation_releases_pix(channel,monkeypatch):
    m,client,result,order,item,owner,buyer=setup_order(channel)
    monkeypatch.setattr(m,'current_user',lambda request:owner)
    assert client.post('/painel/pedidos/'+str(order['id'])+'/status',data={'status':'confirmed'},follow_redirects=False).status_code==303
    monkeypatch.setattr(m,'current_user',lambda request:buyer)
    assert 'data-pix-payment' in client.get(result['redirect']).text
    page=client.get(result['redirect']);assert 'data-customer390="1"' in page.text and 'data-payment390="pix"' in page.text
    monkeypatch.setattr(m,'current_user',lambda request:owner)
    replay=client.post('/painel/pedidos/'+str(order['id'])+'/status',data={'status':'confirmed','return_to':'link'},follow_redirects=False)
    assert replay.status_code==303 and replay.headers['location']=='/pedido/'+order['tracking_token']


def test_custom_message_does_not_replace_store_contact_message(channel,monkeypatch):
    m,client,slug,pid,data,product,buyer=channel
    with m.db() as c:
        owner=dict(c.execute('SELECT u.* FROM users u JOIN professionals p ON p.user_id=u.id WHERE p.id=?',(pid,)).fetchone())
        old=c.execute('SELECT whatsapp_message FROM professionals WHERE id=?',(pid,)).fetchone()[0]
    monkeypatch.setattr(m,'current_user',lambda request:owner)
    assert client.post('/painel/cardapio/whatsapp',data={'mode':'whatsapp','order_message':'Olá, {saudacao}! Meu pedido {pedido} na {loja}: {total}'},follow_redirects=False).status_code==303
    from starlette.requests import Request
    from nowup_storeapp256 import page_context
    with m.db() as c:pro=dict(c.execute('SELECT * FROM professionals WHERE id=?',(pid,)).fetchone())
    request=Request({'type':'http','method':'GET','path':'/painel','headers':[],'query_string':b''})
    assert 'Meu pedido {pedido}' in page_context(vars(m),request,{'pro':pro})['order_message377']
    monkeypatch.setattr(m,'current_user',lambda request:buyer)
    result=client.post('/p/'+slug+'/menu/whatsapp',data=data).json()
    assert 'Meu pedido '+result['order_code'] in result['message'] and '{saudacao}' not in result['message']
    assert result['merchant_url'] in result['message']
    with m.db() as c:assert c.execute('SELECT whatsapp_message FROM professionals WHERE id=?',(pid,)).fetchone()[0]==old


def test_private_order_details_skip_intro_and_do_not_overlay_actions(channel,monkeypatch):
    m,client,result,order,item,owner,buyer=setup_order(channel)
    with m.db() as c:c.execute("UPDATE orders SET order_origin='nowup' WHERE id=?",(order['id'],))
    monkeypatch.setattr(m,'current_user',lambda request:owner)
    page=client.get('/pedido/'+order['tracking_token'])
    assert page.status_code==200
    assert 'id="nowup-opening260"' not in page.text
    assert 'id="order-detail-alerts381"' in page.text
    assert 'Confirmar pedido' in page.text
