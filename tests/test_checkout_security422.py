import json
import pytest
from test_checkout247 import checkout
from nowup_checkout_security422 import validate_cart, check_totals
from fastapi import HTTPException

@pytest.mark.parametrize('field',['price','total','subtotal','delivery_fee','discount','pix_key','payment_confirmed'])
def test_top_level_values_are_rejected_without_creating_order(checkout,field):
    m,client,url,data,_,_=checkout
    response=client.post(url,data={**data,field:'0'},follow_redirects=False)
    assert response.status_code==400
    with m.db() as c: assert c.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==0

@pytest.mark.parametrize('path',['/menu/pedido','/menu/whatsapp'])
@pytest.mark.parametrize('payload',[{'price_cents':1},{'unitPrice':1},{'customization':{'price':1}},{'options':[{'id':1,'price':1}]}])
def test_cart_amounts_are_rejected_in_both_channels(checkout,path,payload):
    m,client,url,data,pid,_=checkout
    with m.db() as c:c.execute("UPDATE professionals SET plan_active='completo' WHERE id=(SELECT professional_id FROM products WHERE id=?)",(pid,))
    data['cart_json']=json.dumps([{'id':pid,'quantity':1,**payload}])
    response=client.post(url.replace('/menu/pedido',path),data=data,follow_redirects=False)
    assert response.status_code==400
    with m.db() as c: assert c.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==0

def make_order(checkout,method='pix',channel='internal'):
    m,client,url,data,pid,customer=checkout
    with m.db() as c:
        pro=c.execute('SELECT professional_id FROM products WHERE id=?',(pid,)).fetchone()[0]
        owner=c.execute('SELECT user_id FROM professionals WHERE id=?',(pro,)).fetchone()[0]
        c.execute("UPDATE professionals SET plan_active='completo',pix_key='12999999999',pix_key_type='phone',pix_receiver_name='SEDE ZERO',pix_receiver_city='UBATUBA' WHERE id=?",(pro,))
    customer.update(name='Cliente de teste',phone='12999999999')
    result=client.post(url if channel=='internal' else url.replace('/menu/pedido','/menu/whatsapp'),data={**data,'payment_method':method},follow_redirects=False)
    assert result.status_code in (200,303),result.text
    with m.db() as c:o=dict(c.execute('SELECT * FROM orders ORDER BY id DESC LIMIT 1').fetchone())
    return m,client,o,owner,customer

@pytest.mark.parametrize('channel',['internal','external'])
def test_pix_is_waiting_in_database_and_values_and_payload_are_server_owned(checkout,channel):
    m,client,o,owner,customer=make_order(checkout,channel=channel)
    assert o['status']=='awaiting_payment' and o['subtotal_cents']==300 and o['total_cents']==300
    with m.db() as c:
        item=c.execute('SELECT unit_price_cents FROM order_items WHERE order_id=?',(o['id'],)).fetchone()
        assert item[0]==300
        assert c.execute('SELECT status FROM order_status_history WHERE order_id=?',(o['id'],)).fetchone()[0]=='awaiting_payment'
        store=c.execute('SELECT * FROM professionals WHERE id=?',(o['professional_id'],)).fetchone()
        pix=m.pix_payment(store,o['total_cents'],'NU'+str(o['id']))
    assert '54043.00' in pix['payload'] and 'key' not in pix
    page=client.get('/pedido/'+o['tracking_token']);assert page.status_code==200
    assert 'data-pix-payment' in page.text
    assert 'Chave Pix: <strong>' not in page.text

@pytest.mark.parametrize('target',['preparing','ready','out_for_delivery','completed'])
def test_pix_cannot_advance_even_after_acceptance_without_manual_bank_check(checkout,monkeypatch,target):
    m,client,o,owner,_=make_order(checkout)
    monkeypatch.setattr(m,'current_user',lambda r:{'id':owner,'role':'professional'})
    path='/painel/pedidos/'+str(o['id'])
    assert client.post(path+'/status',data={'status':'confirmed'},headers={'Accept':'application/json'}).status_code==200
    denied=client.post(path+'/status',data={'status':target},headers={'Accept':'application/json'})
    assert denied.status_code==409
    with m.db() as c:assert c.execute('SELECT status FROM orders WHERE id=?',(o['id'],)).fetchone()[0]=='confirmed'
    assert client.post(path+'/conferir-pix',headers={'Accept':'application/json'}).status_code==200
    assert client.post(path+'/status',data={'status':target},headers={'Accept':'application/json'}).status_code==200

def test_direct_manual_pix_approval_authenticates_owner_and_does_not_start_preparation(checkout,monkeypatch):
    m,client,o,owner,customer=make_order(checkout)
    path='/painel/pedidos/'+str(o['id'])+'/conferir-pix'
    assert client.post(path).status_code==403
    monkeypatch.setattr(m,'current_user',lambda r:{'id':owner+10000,'role':'professional'})
    assert client.post(path).status_code==404
    monkeypatch.setattr(m,'current_user',lambda r:{'id':owner,'role':'professional'})
    assert client.post(path,headers={'Accept':'application/json'}).status_code==200
    with m.db() as c:
        current=c.execute('SELECT * FROM orders WHERE id=?',(o['id'],)).fetchone()
        assert current['status']=='new' and m.nowup_notinha401.payment_checked(c,current)
    assert client.post('/painel/pedidos/'+str(o['id'])+'/status',data={'status':'confirmed'},headers={'Accept':'application/json'}).status_code==200
    with m.db() as c:c.execute('UPDATE orders SET total_cents=total_cents+1 WHERE id=?',(o['id'],))
    response=client.post('/painel/pedidos/'+str(o['id'])+'/status',data={'status':'preparing'},headers={'Accept':'application/json'})
    assert response.status_code==409

def test_cash_keeps_existing_status_and_store_and_product_scope_are_checked(checkout):
    m,client,url,data,pid,_=checkout
    bad=client.post(url,data={**data,'store_id':'999999'},follow_redirects=False)
    assert bad.status_code==400
    m,client,o,_,_=make_order(checkout,'cash')
    assert o['status']=='new'

def test_current_database_price_and_delivery_are_used(checkout):
    m,client,url,data,pid,_=checkout
    with m.db() as c:
        c.execute('UPDATE products SET price_cents=750 WHERE id=?',(pid,))
        c.execute("UPDATE professionals SET allows_delivery=1,delivery_fee_cents=425 WHERE id=(SELECT professional_id FROM products WHERE id=?)",(pid,))
    data.update(fulfillment_type='delivery',address='Rua de teste, 1',cart_json=json.dumps([{'id':pid,'quantity':2}]))
    result=client.post(url,data=data,follow_redirects=False);assert result.status_code==303,result.text
    with m.db() as c:
        o=c.execute('SELECT * FROM orders').fetchone();assert (o['subtotal_cents'],o['delivery_fee_cents'],o['total_cents'])==(1500,425,1925)

def test_choices_and_weight_survive_input_contract():
    validate_cart([{'id':1,'quantity':1,'options':[{'id':3,'quantity':2}],'weight_grams370':350,'notes':'sem cebola','customization':{'groups':{'1':['2']},'removed':['cebola']},'utensils':True}])
    with pytest.raises(HTTPException):check_totals(100,-1,99)
    with pytest.raises(HTTPException):check_totals(100,20,1)


def test_customer_and_merchant_see_payment_before_items_are_accepted(checkout,monkeypatch):
    m,client,o,owner,customer=make_order(checkout)
    monkeypatch.setattr(m,'current_user',lambda r:{'id':owner,'role':'professional'})
    endpoint='/painel/pedidos/'+str(o['id'])+'/conferir-pix'
    assert client.post(endpoint,headers={'Accept':'application/json'}).json()['payment_confirmed']
    assert client.post(endpoint,headers={'Accept':'application/json'}).json()['payment_confirmed']
    monkeypatch.setattr(m,'current_user',lambda r:customer)
    page=client.get('/pedido/'+o['tracking_token'])
    assert 'data-pix-confirmed405' in page.text and 'data-pix-payment' not in page.text
    assert client.get('/pedido/'+o['tracking_token']+'/status').json()['payment_confirmed']
    monkeypatch.setattr(m,'current_user',lambda r:{'id':owner,'role':'professional'})
    assert 'data-pix-confirmed405' in client.get('/pedido/'+o['tracking_token']).text

@pytest.mark.parametrize('store',['-1','bad','9'*5000])
def test_invalid_store_identifiers_return_validation_error(checkout,store):
    _,client,url,data,_,_=checkout
    assert client.post(url,data={**data,'store_id':store}).status_code==400
