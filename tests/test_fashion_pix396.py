import json
import pytest
from bs4 import BeautifulSoup
from test_checkout247 import checkout
from test_storeapp256 import shop
from test_storeapp257 import channel
from test_order_link377 import setup_order
from test_pix import parse


def fashion_order(channel):
    m,client,result,order,item,owner,buyer=setup_order(channel)
    with m.db() as c:
        c.execute("UPDATE professionals SET business_type='fashion' WHERE id=?",(order['professional_id'],))
        c.execute("UPDATE orders SET payment_method='on_delivery' WHERE id=?",(order['id'],))
    return m,client,result,order,owner,buyer


def test_agreed_pix_is_owner_only_and_releases_confirmed_total(channel,monkeypatch):
    m,client,result,order,owner,buyer=fashion_order(channel)
    endpoint=f"/painel/pedidos/{order['id']}/pix-combinado"
    assert client.post(endpoint).status_code==403
    monkeypatch.setattr(m,'current_user',lambda request:dict(owner,id=owner['id']+10000))
    assert client.post(endpoint).status_code==404
    monkeypatch.setattr(m,'current_user',lambda request:owner)
    assert client.post(endpoint).status_code==409  # must confirm first
    assert client.post(f"/painel/pedidos/{order['id']}/status",data={'status':'confirmed'},follow_redirects=False).status_code==303
    page=client.get('/pedido/'+order['tracking_token'])
    assert 'Liberar Pix combinado com o cliente' in page.text
    assert 'data-pix-payment' not in page.text
    assert client.post(endpoint,follow_redirects=False).status_code==303
    with m.db() as c:
        saved=dict(c.execute('SELECT * FROM orders WHERE id=?',(order['id'],)).fetchone())
        assert saved['payment_method']=='pix' and saved['status']=='confirmed'
        assert saved['total_cents']==order['total_cents']
    assert client.post(endpoint,follow_redirects=False).status_code==303
    with m.db() as c:
        assert c.execute('SELECT updated_at FROM orders WHERE id=?',(order['id'],)).fetchone()[0]==saved['updated_at']
    monkeypatch.setattr(m,'current_user',lambda request:buyer)
    page=client.get(result['redirect'])
    node=BeautifulSoup(page.text,'html.parser').select_one('[data-pix-payment] script')
    assert node and parse(json.loads(node.string)['payload'])['54']==f"{order['total_cents']/100:.2f}"
    assert json.loads(node.string)['confirmation']=='Confirmação do pagamento feita pela loja.'
    assert 'pix-combinado' not in page.text


@pytest.mark.parametrize('status',['new','reviewing','awaiting_approval','revision_approved','completed','cancelled','rejected'])
def test_agreed_pix_cannot_bypass_revision_or_reopen_closed_order(channel,monkeypatch,status):
    m,client,result,order,owner,buyer=fashion_order(channel)
    with m.db() as c:c.execute('UPDATE orders SET status=? WHERE id=?',(status,order['id']))
    monkeypatch.setattr(m,'current_user',lambda request:owner)
    assert client.post(f"/painel/pedidos/{order['id']}/pix-combinado").status_code==409
    with m.db() as c:assert c.execute('SELECT payment_method FROM orders WHERE id=?',(order['id'],)).fetchone()[0]=='on_delivery'


@pytest.mark.parametrize('bad',['missing_key','other_payment','other_store_type'])
def test_agreed_pix_requires_valid_store_settings_and_combined_payment(channel,monkeypatch,bad):
    m,client,result,order,owner,buyer=fashion_order(channel)
    with m.db() as c:
        c.execute("UPDATE orders SET status='confirmed' WHERE id=?",(order['id'],))
        if bad=='missing_key':c.execute("UPDATE professionals SET pix_key_type='' WHERE id=?",(order['professional_id'],))
        if bad=='other_payment':c.execute("UPDATE orders SET payment_method='cash' WHERE id=?",(order['id'],))
        if bad=='other_store_type':c.execute("UPDATE professionals SET business_type='store' WHERE id=?",(order['professional_id'],))
    monkeypatch.setattr(m,'current_user',lambda request:owner)
    assert client.post(f"/painel/pedidos/{order['id']}/pix-combinado").status_code==409
