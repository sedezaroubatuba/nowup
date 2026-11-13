from bs4 import BeautifulSoup
from test_merchant228 import env
from nowup_whatsapp_status421 import DEFAULTS, STATUSES, initialize, settings


def test_migration_is_idempotent_and_defaults_include_confirmation(env):
    m, _, _, pid, _ = env
    with m.db() as c:
        initialize(c); initialize(c)
        assert settings(c, pid)['templates'] == DEFAULTS
    assert len(STATUSES) == 6 and 'confirmed' in DEFAULTS


def test_configuration_is_per_store_and_restore_and_toggle_work(env):
    m, client, _, pid, other = env
    data={**DEFAULTS, 'confirmed': 'Confirmação da {{nome_loja}} para {{nome_cliente}}: {{numero_pedido}}', 'enabled':'1'}
    result=client.post('/painel/cardapio/mensagens-whatsapp',data=data,follow_redirects=False)
    assert result.status_code==303
    with m.db() as c:
        assert settings(c,pid)['templates']['confirmed']==data['confirmed']
        assert settings(c,other)['templates']==DEFAULTS
    page=client.get('/painel/cardapio/mensagens-whatsapp')
    assert page.status_code==200 and data['confirmed'] in page.text
    result=client.post('/painel/cardapio/mensagens-whatsapp',data={**data,'enabled':''},follow_redirects=False)
    assert result.status_code==303
    with m.db() as c: assert settings(c,pid)['enabled'] is False
    assert client.post('/painel/cardapio/mensagens-whatsapp',data={'action':'restore','enabled':'1'},follow_redirects=False).status_code==303
    with m.db() as c: assert settings(c,pid)=={'enabled':True,'templates':DEFAULTS}


def test_validation_and_authentication(env):
    m,client,_,pid,_=env
    before=client.get('/painel/cardapio/mensagens-whatsapp').text
    for data in ({}, {**DEFAULTS,'new':'x'*1501}):
        assert client.post('/painel/cardapio/mensagens-whatsapp',data=data).status_code==400
    assert client.get('/painel/cardapio/mensagens-whatsapp').text==before
    from fastapi.testclient import TestClient
    guest=TestClient(m.app,headers={'Origin':'http://testserver'})
    assert guest.get('/painel/cardapio/mensagens-whatsapp').status_code==401
    assert guest.post('/painel/cardapio/mensagens-whatsapp',data=DEFAULTS).status_code==401
    guest.close()


def test_cardapio_status_link_data_and_mutation_leave_vitrine_untouched(env):
    m,client,ids,pid,_=env
    with m.db() as c:
        oid=c.execute('''INSERT INTO orders(professional_id,customer_name,customer_phone,status,total_cents,created_at,updated_at,fulfillment_type,order_origin,tracking_token,order_code)
          VALUES(?,?,?,?,?,?,?,?,?,?,?)''',(pid,'José <b> & Ana','(12) 99999-9999','new',1000,m.now_iso(),m.now_iso(),'delivery','external','manual421','NU-421')).lastrowid
        c.execute("INSERT INTO order_items(order_id,product_name,quantity,unit_price_cents) VALUES(?,'Água',1,1000)",(oid,))
        before=[tuple(r) for r in c.execute("SELECT id,status FROM orders WHERE COALESCE(order_origin,'legacy')<>'external'")]
    post=client.post(f'/painel/pedidos/{oid}/status',data={'status':'confirmed'},headers={'Accept':'application/json','X-NowUp-WhatsApp-Central':'1'})
    assert post.status_code==200 and post.json()['status']=='confirmed'
    page=client.get('/painel/cardapio/pedidos')
    soup=BeautifulSoup(page.text,'html.parser')
    box=soup.select_one(f'[data-wa-status421="{oid}"]')
    assert box['data-status421']=='confirmed' and box['data-phone421']=='(12) 99999-9999'
    assert box['data-customer421']=='José <b> & Ana'
    assert not box.select_one('b')
    assert box.select_one('[data-wa-send421]')['target']=='_blank'
    assert soup.select_one('#wa-config421')
    assert 'data-wa-status421' not in client.get('/painel').text
    with m.db() as c:
        assert [tuple(r) for r in c.execute("SELECT id,status FROM orders WHERE COALESCE(order_origin,'legacy')<>'external'")]==before
    fragment=client.get('/painel/cardapio/pedidos?fragment=1')
    assert f'data-wa-status421="{oid}"' in fragment.text
    assert client.post(f'/painel/pedidos/{oid}/conferir-pix',headers={'Accept':'application/json'}).status_code==200
    for status in ('preparing','out_for_delivery','completed'):
        assert client.post(f'/painel/pedidos/{oid}/status',data={'status':status},headers={'Accept':'application/json'}).json()['status']==status
    assert 'data-status421="completed"' in client.get('/painel/cardapio/pedidos?fragment=1').text
