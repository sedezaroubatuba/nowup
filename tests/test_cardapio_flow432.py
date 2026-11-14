from test_merchant228 import env
from bs4 import BeautifulSoup
from test_checkout247 import checkout
from test_storeapp256 import shop
from test_storeapp257 import channel
from test_order_link377 import setup_order

def test_full_internal_cardapio_pix_statuses(channel,monkeypatch):
    m,client,result,o,item,owner,buyer=setup_order(channel)
    assert result['internal_checkout432'] and result['confirmed'] and not result['whatsapp_only']
    assert 'pix' not in result
    with m.db() as c:
        assert c.execute('SELECT status FROM orders WHERE id=?',(o['id'],)).fetchone()[0]=='new'
        assert c.execute("SELECT COUNT(*) FROM notifications WHERE user_id=? AND title='Novo pedido no NowUp'",(owner['id'],)).fetchone()[0]==1
    page=client.get(result['redirect']);assert page.status_code==200
    assert not BeautifulSoup(page.text,'html.parser').select('[data-pix-payment]')
    monkeypatch.setattr(m,'current_user',lambda r:owner)
    endpoint='/painel/pedidos/'+str(o['id'])+'/status'
    r=client.post(endpoint,data={'status':'confirmed'},headers={'Accept':'application/json'});assert r.status_code==200,r.text
    monkeypatch.setattr(m,'current_user',lambda r:buyer)
    page=client.get(result['redirect']);soup=BeautifulSoup(page.text,'html.parser')
    assert soup.select('[data-pix-payment]')
    assert 'data-store-whatsapp432' in page.text
    monkeypatch.setattr(m,'current_user',lambda r:owner)
    assert client.post('/painel/pedidos/'+str(o['id'])+'/conferir-pix',headers={'Accept':'application/json'}).status_code==200
    for state in ['ready','out_for_delivery','completed']:
        with m.db() as c:c.execute("UPDATE orders SET fulfillment_type='delivery' WHERE id=?",(o['id'],))
        r=client.post(endpoint,data={'status':state},headers={'Accept':'application/json'});assert r.status_code==200,r.text
    monkeypatch.setattr(m,'current_user',lambda r:buyer)
    page=client.get(result['redirect'])
    assert 'Seu pagamento foi aprovado. Aguarde os próximos status' in page.text
    with m.db() as c:assert c.execute('SELECT status FROM orders WHERE id=?',(o['id'],)).fetchone()[0]=='completed'

def test_saved_merchant_session_survives_return_and_logout_revokes(env):
    from fastapi.testclient import TestClient
    m,_,ids,pid,other=env
    m.nowup_push75.initialize()
    with m.db() as c:uid=c.execute('SELECT user_id FROM professionals WHERE id=?',(pid,)).fetchone()[0]
    response=m.create_session_response(uid,'/painel')
    from http.cookies import SimpleCookie
    cookies=SimpleCookie();cookies.load(response.headers['set-cookie'])
    token=cookies['nowup_session'].value
    assert int(cookies['nowup_session']['max-age'])>86400
    client=TestClient(m.app,headers={'Origin':'http://testserver'},follow_redirects=False)
    client.cookies.set('nowup_session',token)
    for _ in range(3):
        r=client.get('/sessao420');assert r.json()['authenticated'] and r.json()['role']=='professional'
    client.post('/sair')
    assert not client.get('/sessao420').json()['authenticated']
