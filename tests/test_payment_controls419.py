from bs4 import BeautifulSoup
from test_checkout247 import checkout
from test_storeapp256 import shop
from test_storeapp257 import channel
from test_order_link377 import setup_order


def test_owner_confirms_pix_in_payment_tab_buyer_cannot(channel,monkeypatch):
    m,client,result,o,item,owner,buyer=setup_order(channel)
    with m.db() as c:m.nowup_notinha401.initialize(c)
    monkeypatch.setattr(m,'current_user',lambda r:owner)
    path='/pedido/'+o['tracking_token']
    assert not BeautifulSoup(client.get(path).text,'html.parser').select('[data-confirm-pix419]')
    client.post('/painel/pedidos/'+str(o['id'])+'/status',data={'status':'confirmed'},headers={'Accept':'application/json'})
    payment=BeautifulSoup(client.get(path).text,'html.parser').select_one('#pagamento377')
    form=payment.select_one('[data-confirm-pix419]');assert form and form.select_one('input[type=checkbox][required]')
    assert 'Confirmar Pix recebido' in form.text
    assert payment.select_one('details.nu419-preview [data-pix-payment]')
    monkeypatch.setattr(m,'current_user',lambda r:buyer)
    customer=BeautifulSoup(client.get(result['redirect']).text,'html.parser')
    assert not customer.select('[data-confirm-pix419],details.nu419-preview') and customer.select('[data-pix-payment]')
    endpoint='/painel/pedidos/'+str(o['id'])+'/conferir-pix'
    assert client.post(endpoint,headers={'Accept':'application/json'}).status_code==403
    monkeypatch.setattr(m,'current_user',lambda r:owner)
    response=client.post(endpoint,headers={'Accept':'application/json'},follow_redirects=False)
    assert response.status_code==200 and response.json()['payment_confirmed']
    for viewer,url in [(owner,path),(buyer,result['redirect'])]:
        monkeypatch.setattr(m,'current_user',lambda r,viewer=viewer:viewer)
        page=BeautifulSoup(client.get(url).text,'html.parser')
        assert page.select('[data-pix-confirmed405]') and not page.select('[data-confirm-pix419]')


def test_central_detail_shows_receipt_before_confirmation_controls(channel,monkeypatch):
    m,client,result,o,item,owner,buyer=setup_order(channel)
    with m.db() as c:m.nowup_notinha401.initialize(c)
    monkeypatch.setattr(m,'current_user',lambda r:owner)
    endpoint='/painel/pedidos/'+str(o['id'])+'/detalhes407?central=1'
    response=client.get(endpoint);assert response.status_code==200
    soup=BeautifulSoup(response.text,'html.parser');assert soup.select_one('.nu401-paper')
    assert item['product_name'] in soup.select_one('.nu401-paper').text
    assert response.text.index('nu401-paper')<response.text.index('data-confirm390')
    accepted=client.post('/painel/pedidos/'+str(o['id'])+'/status',data={'status':'confirmed'},headers={'Accept':'application/json','X-NowUp-Order-Detail':'1','X-NowUp-WhatsApp-Central':'1'})
    assert accepted.status_code==200 and 'nu401-paper' in accepted.json()['html407']
