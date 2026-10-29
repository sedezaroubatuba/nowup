import json
from urllib.parse import urlsplit,parse_qs
import pytest
from test_storeapp256 import shop
from test_checkout247 import checkout

@pytest.fixture
def channel(shop,monkeypatch):
    m,client,slug,pid,url,data,product=shop
    with m.db() as c:
        customer=dict(c.execute("SELECT * FROM users WHERE email='audit247@example.invalid'").fetchone())
        c.execute("UPDATE professionals SET whatsapp='12999999999' WHERE id=?",(pid,))
    customer.update(name='Maria da conta',phone='12988887777')
    monkeypatch.setattr(m,'current_user',lambda request:customer)
    return m,client,slug,pid,dict(data),product,customer

@pytest.mark.parametrize('mode',['panel','whatsapp','both'])
def test_channels_identity_totals_and_idempotency(channel,mode):
    m,client,slug,pid,data,product,customer=channel
    with m.db() as c:c.execute('INSERT INTO store_menu257(professional_id,whatsapp,mode) VALUES(?,?,?)',(pid,'5512987776666',mode))
    data['cart_json']=json.dumps([{'id':product,'quantity':2,'price':1}]);data['customer_name']='Nome adulterado'
    endpoint='/p/'+slug+'/menu/whatsapp'
    response=client.post(endpoint,data=data);assert response.status_code==200,response.text
    result=response.json();assert result['prepared'] and result['total_cents']==600 and result['mode']==mode
    assert 'Maria da conta' in result['message'] and '12988887777' in result['message']
    assert 'Nome adulterado' not in result['message'] and '2x Auditoria' in result['message']
    assert result['recorded']==(mode!='whatsapp')
    if mode!='panel':assert result['whatsapp_url'].startswith('https://wa.me/5512987776666?text=')
    else:assert 'whatsapp_url' not in result
    if mode!='whatsapp':
        assert client.post(endpoint,data=data).json()==result
        with m.db() as c:
            order=c.execute('SELECT * FROM orders').fetchone()
            assert order['customer_id']==customer['id'] and order['customer_name']=='Maria da conta'
            assert order['customer_phone']=='12988887777' and order['order_origin']=='external'
            assert c.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==1
            assert c.execute("SELECT COUNT(*) FROM notifications WHERE title='Novo pedido no NowUp'").fetchone()[0]==1
        assert client.get(result['redirect']).status_code==200
        data['notes']='alterado';assert client.post(endpoint,data=data).status_code==409
    else:
        with m.db() as c:assert c.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==0


def test_default_is_both_and_marketplace_remains_internal(channel):
    m,client,slug,pid,data,product,customer=channel
    result=client.post('/p/'+slug+'/menu/whatsapp',data=data);assert result.status_code==200,result.text
    assert result.json()['mode']=='both' and result.json()['recorded']
    data['request_key']='separate-marketplace-request257'
    native=client.post('/p/'+slug+'/menu/pedido',data=data,headers={'Accept':'application/json'})
    assert native.status_code==200 and native.json()['confirmed']
    with m.db() as c:assert c.execute('SELECT order_origin FROM orders ORDER BY id DESC LIMIT 1').fetchone()[0]=='nowup'


def test_anonymous_cannot_prepare_any_channel(channel,monkeypatch):
    m,client,slug,pid,data,product,customer=channel
    monkeypatch.setattr(m,'current_user',lambda request:None)
    assert client.post('/p/'+slug+'/menu/whatsapp',data=data).status_code==401
    page=client.get('/p/'+slug+'/menu?loja=1');assert page.status_code==200
    assert 'data-login-required="1"' in page.text and 'Entrar para pedir' in page.text
    assert 'name="customer_phone"' in page.text


@pytest.mark.parametrize('mode',['loja=1','origem=externo','auto'])
def test_independent_checkout_destination(channel,mode):
    m,client,slug,pid,data,product,customer=channel
    if mode=='auto':
        with m.db() as c:c.execute("UPDATE professionals SET plan_active='cardapio' WHERE id=?",(pid,))
    page=client.get('/p/'+slug+'/menu'+('' if mode=='auto' else '?'+mode));assert page.status_code==200,page.text
    assert 'action="/p/'+slug+'/menu/whatsapp"' in page.text
    assert '"whatsappCheckout": true' in page.text
    if mode!='auto':assert '"whatsappCheckout": false' in client.get('/p/'+slug+'/menu').text


@pytest.mark.parametrize('state',['blocked','closed','disabled','vitrine'])
def test_store_state(channel,state):
    m,client,slug,pid,data,product,customer=channel
    with m.db() as c:
        if state=='blocked':c.execute('UPDATE professionals SET blocked=1 WHERE id=?',(pid,))
        elif state=='closed':c.execute("UPDATE professionals SET business_status='paused' WHERE id=?",(pid,))
        elif state=='disabled':c.execute('UPDATE users SET is_active=0 WHERE id=(SELECT user_id FROM professionals WHERE id=?)',(pid,))
        else:c.execute("UPDATE professionals SET plan_active='vitrine' WHERE id=?",(pid,))
    assert client.post('/p/'+slug+'/menu/whatsapp',data=data).status_code in (404,409)


def test_delivery_quote_and_cross_store_item(channel):
    m,client,slug,pid,data,product,customer=channel
    with m.db() as c:c.execute('UPDATE professionals SET allows_delivery=1,delivery_fee_cents=500 WHERE id=?',(pid,))
    data.update(fulfillment_type='delivery',address='',neighborhood='Centro')
    assert client.post('/p/'+slug+'/menu/whatsapp',data=data).status_code==400
    data.update(address='Rua A, 12',notes='Sem sacola',address_reference='Portão azul',save_address='1')
    response=client.post('/p/'+slug+'/menu/whatsapp',data=data);assert response.status_code==200,response.text
    assert response.json()['total_cents']==800 and 'Portão azul' in response.json()['message']
    with m.db() as c:assert c.execute('SELECT address FROM users WHERE id=?',(customer['id'],)).fetchone()[0]=='Rua A, 12'
    data['request_key']='cross-store-request-257';data['cart_json']=json.dumps([{'id':999999,'quantity':1}])
    assert client.post('/p/'+slug+'/menu/whatsapp',data=data).status_code==400


def test_merchant_saves_only_own_config(channel,monkeypatch):
    m,client,slug,pid,data,product,customer=channel
    with m.db() as c:owner=dict(c.execute('SELECT u.* FROM users u JOIN professionals p ON p.user_id=u.id WHERE p.id=?',(pid,)).fetchone())
    monkeypatch.setattr(m,'current_user',lambda request:owner)
    result=client.post('/painel/cardapio/whatsapp',data={'whatsapp':'https://wa.me/5512988887777','mode':'panel'},follow_redirects=False)
    assert result.status_code==303,result.text
    with m.db() as c:
        setting=c.execute('SELECT * FROM store_menu257 WHERE professional_id=?',(pid,)).fetchone()
        assert setting['whatsapp']=='5512988887777' and setting['mode']=='panel'
        assert c.execute('SELECT whatsapp FROM professionals WHERE id=?',(pid,)).fetchone()[0]=='12999999999'
    assert client.post('/p/'+slug+'/menu/whatsapp',data=data).status_code==403
    monkeypatch.setattr(m,'current_user',lambda request:customer)
    assert client.post('/painel/cardapio/whatsapp',data={'mode':'both','whatsapp':'12999999999'}).status_code==403


@pytest.mark.parametrize('number',['https://evil.invalid/5512999999999','https://wa.me.evil.invalid/5512999999999','https://wa.me/123','javascript:alert(1)','00000000000'])
def test_destination_validation(number):
    from nowup_storeapp257 import phone
    from fastapi import HTTPException
    with pytest.raises(HTTPException):phone(number)
