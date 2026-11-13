"""Dedicated WhatsApp central uses existing authorized orders and mutations."""
from bs4 import BeautifulSoup
from test_checkout247 import checkout
from test_storeapp256 import shop
from test_storeapp257 import channel
from test_order_link377 import setup_order

JSON={'Accept':'application/json','X-NowUp-Order-Detail':'1'}

def test_ten_cards_actions_payment_and_channel_isolation(channel,monkeypatch):
    m,client,result,o,item,owner,buyer=setup_order(channel)
    with m.db() as c:
        m.nowup_notinha401.initialize(c)
        for i in range(9):
            cur=c.execute("INSERT INTO orders(professional_id,customer_id,customer_name,status,total_cents,subtotal_cents,created_at,updated_at,fulfillment_type,order_origin,tracking_token,order_code,payment_method) VALUES(?,?,'Cliente central','new',300,300,?,?,'pickup','external',?,?,'cash')",(o['professional_id'],buyer['id'],m.now_iso(),m.now_iso(),'central418-'+str(i),'NU-CENTRAL-'+str(i)))
            c.execute("INSERT INTO order_items(order_id,product_name,quantity,unit_price_cents) VALUES(?,'Produto central',1,300)",(cur.lastrowid,))
        c.execute("INSERT INTO orders(professional_id,customer_name,status,total_cents,created_at,updated_at,order_origin) VALUES(?,'ONLY-VITRINE-418','new',300,?,?,'nowup')",(o['professional_id'],m.now_iso(),m.now_iso()))
        other=c.execute('SELECT id FROM professionals WHERE id<>? LIMIT 1',(o['professional_id'],)).fetchone()[0]
        foreign=c.execute("INSERT INTO orders(professional_id,customer_name,status,created_at,updated_at,order_origin) VALUES(?,'OTHER-STORE-418','new',?,?,'external')",(other,m.now_iso(),m.now_iso())).lastrowid
    assert client.get('/painel/cardapio/pedidos').status_code==403
    monkeypatch.setattr(m,'current_user',lambda request:owner)
    page=client.get('/painel/cardapio/pedidos');assert page.status_code==200
    soup=BeautifulSoup(page.text,'html.parser');assert len(soup.select('[data-menu-order408]'))==10
    assert 'ONLY-VITRINE-418' not in page.text and 'OTHER-STORE-418' not in page.text
    assert soup.select_one('[data-search418]') and soup.select_one('[data-central-dialog418]')
    card=soup.select_one('[data-menu-order408="'+str(o['id'])+'"]')
    assert card.select_one('button[value=confirmed]') and 'Aguardando Confirmação de Pagamento' in card.text
    assert client.get('/painel/pedidos/'+str(foreign)+'/detalhes407?central=1').status_code==404
    path='/painel/pedidos/'+str(o['id'])
    accepted=client.post(path+'/status',data={'status':'confirmed'},headers=JSON,follow_redirects=False)
    assert accepted.status_code==200 and accepted.json()['id']==o['id'] and 'html407' in accepted.json()
    paid=client.post(path+'/conferir-pix',headers=JSON,follow_redirects=False)
    assert paid.status_code==200 and paid.json()['payment_confirmed'] is True and 'location' not in paid.headers
    fragment=client.get('/painel/cardapio/pedidos?fragment=1');assert fragment.status_code==200
    assert 'Pix recebido e confirmado' in fragment.text
    from datetime import datetime
    with m.db() as c:
        lower,upper=m.order_day_bounds(datetime.now(m.SAO_PAULO_TZ).date())
        main=m.nowup_merchant228.board(c,o['professional_id'],lower,upper,m.SAO_PAULO_TZ)
        names=[r['customer_name'] for stage in main['stages'] for r in stage['orders']]
    assert 'Cliente central' not in names and 'ONLY-VITRINE-418' in names


def test_review_json_keeps_customer_approval_and_refusal_requires_reason(channel,monkeypatch):
    m,client,result,o,item,owner,buyer=setup_order(channel)
    with m.db() as c:m.nowup_notinha401.initialize(c)
    monkeypatch.setattr(m,'current_user',lambda request:owner)
    path='/painel/pedidos/'+str(o['id'])
    revision={'keep':str(item['id']),'qty_'+str(item['id']):'2','price_'+str(item['id']):'3.00'}
    response=client.post(path+'/revisao',data=revision,headers=JSON,follow_redirects=False)
    assert response.status_code==200 and response.json()['status']=='awaiting_approval' and 'location' not in response.headers
    with m.db() as c:assert c.execute('SELECT total_cents FROM orders WHERE id=?',(o['id'],)).fetchone()[0]==300
    assert client.post(path+'/status',data={'status':'confirmed'},headers=JSON).status_code==409
    rejected=client.post(path+'/status',data={'status':'rejected','reason':'Produto indisponível'},headers=JSON,follow_redirects=False)
    assert rejected.status_code==200 and rejected.json()['status']=='rejected'
    page=client.get('/painel/cardapio/pedidos');assert 'confira eventual devolução do Pix' in page.text


def test_central_detail_excludes_own_vitrine_and_unauthenticated_users(channel,monkeypatch):
    m,client,result,o,item,owner,buyer=setup_order(channel)
    with m.db() as c:
        m.nowup_notinha401.initialize(c);c.execute("UPDATE orders SET order_origin='nowup' WHERE id=?",(o['id'],))
    monkeypatch.setattr(m,'current_user',lambda request:owner)
    path='/painel/pedidos/'+str(o['id'])+'/detalhes407'
    assert client.get(path).status_code==200 and client.get(path+'?central=1').status_code==404
    monkeypatch.setattr(m,'current_user',lambda request:None)
    assert client.get('/painel/cardapio/pedidos?fragment=1').status_code==401
