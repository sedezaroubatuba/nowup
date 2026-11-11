import json,secrets
from urllib.parse import urlsplit,parse_qs
import pytest
from test_merchant228 import env

@pytest.fixture
def checkout(env):
    m,client,_,pid,other=env
    with m.db() as c:
        product=c.execute("INSERT INTO products(professional_id,name,category,price_cents,available,extras_mode,created_at,updated_at) VALUES(?,'Coca 411','Bebidas',500,1,'none',?,?)",(pid,m.now_iso(),m.now_iso())).lastrowid
        foreign=c.execute("INSERT INTO products(professional_id,name,price_cents,available,created_at,updated_at) VALUES(?,'Foreign411',100,1,?,?)",(other,m.now_iso(),m.now_iso())).lastrowid
    return m,client,pid,product,foreign

def open_sale(client,service='counter'):
    r=client.post('/painel/checkout/abrir',data={'service':service,'token':secrets.token_urlsafe(24)},follow_redirects=False)
    assert r.status_code==303,r.text
    return int(parse_qs(urlsplit(r.headers['location']).query)['sale'][0])

def get(client,sid):return client.get('/painel/checkout/vendas/'+str(sid)).json()
def change(client,sid,action,**data):
    version=data.pop('version',get(client,sid)['version'])
    return client.post('/painel/checkout/vendas/'+str(sid)+'/alterar',data={'version':version,'action':action,**data},headers={'Accept':'application/json'})

def test_named_table_one_account_and_mixed_payments(checkout):
    m,client,pid,product,_=checkout
    name='Mesa azul '+secrets.token_hex(3)
    assert client.post('/painel/checkout/mesas',data={'name':name},follow_redirects=False).status_code==303
    client.post('/painel/checkout/mesas',data={'name':name.upper()},follow_redirects=False)
    with m.db() as c:
        tables=c.execute('SELECT * FROM checkout_tables411 WHERE professional_id=? AND name=?',(pid,name)).fetchall();assert len(tables)==1;tid=tables[0]['id']
    opened=client.post(f'/painel/checkout/mesas/{tid}/abrir',follow_redirects=False)
    sid=int(parse_qs(urlsplit(opened.headers['location']).query)['sale'][0])
    again=client.post(f'/painel/checkout/mesas/{tid}/abrir',follow_redirects=False);assert again.headers['location']==opened.headers['location']
    assert change(client,sid,'item',product_id=product,quantity=40).status_code==200
    assert get(client,sid)['total_cents']==20000
    for method in ['credit','cash','pix']:
        assert change(client,sid,'payment',method=method,amount='50,00').status_code==200
    s=get(client,sid);assert s['paid']==15000 and s['remaining']==5000
    assert change(client,sid,'close').status_code==400
    assert change(client,sid,'payment',method='cash',amount='50,01').status_code==400
    assert change(client,sid,'payment',method='cash',amount='50,00').status_code==200
    assert change(client,sid,'close').status_code==200
    assert get(client,sid)['status']=='completed'
    assert change(client,sid,'item',product_id=product).status_code==409
    receipt=client.get(f'/painel/checkout/vendas/{sid}/imprimir');assert receipt.status_code==200 and '200,00' in receipt.text
    assert 'Coca 411' in receipt.text
    closed=client.get('/painel/checkout?tab=closed');assert name in closed.text
    fresh=client.post(f'/painel/checkout/mesas/{tid}/abrir',follow_redirects=False);assert fresh.headers['location']!=opened.headers['location']
    assert get(client,sid)['status']=='completed'


def test_owner_code_search_server_prices_stale_tabs_and_corrections(checkout):
    m,client,pid,product,foreign=checkout
    sid=open_sale(client)
    data=client.get('/painel/checkout/catalogo?q='+str(product)).json()['products'];assert data[0]['id']==product
    assert not client.get('/painel/checkout/catalogo?q='+str(foreign)).json()['products']
    assert change(client,sid,'item',product_id=foreign).status_code==400
    first=change(client,sid,'item',product_id=product,quantity=2);assert first.status_code==200
    old=first.json()['version']
    assert change(client,sid,'payment',method='pix',amount='5,00',version=old).status_code==200
    assert change(client,sid,'payment',method='pix',amount='5,00',version=old).status_code==409
    assert get(client,sid)['paid']==500
    item=get(client,sid)['items'][0]['id'];assert change(client,sid,'remove_item',item_id=item).status_code==400
    pay=get(client,sid)['payments'][0]['id'];assert change(client,sid,'remove_payment',payment_id=pay,reason='Lançamento incorreto').status_code==200
    assert get(client,sid)['remaining']==1000
    assert change(client,sid,'payment',method='cash',amount='-1').status_code==400
    client.cookies.clear();client.cookies.set('nowup_session','other-test')
    try:
        assert client.get(f'/painel/checkout/vendas/{sid}').status_code==404
        assert client.post(f'/painel/checkout/vendas/{sid}/alterar',data={'version':old,'action':'close'},headers={'Accept':'application/json'}).status_code==404
        assert client.get(f'/painel/checkout/vendas/{sid}/imprimir').status_code==404
    finally:client.cookies.clear();client.cookies.set('nowup_session','merchant-test')


def test_report_breakdown_and_weighted_product(checkout):
    m,client,pid,product,_=checkout
    with m.db() as c:
        weighted=c.execute("INSERT INTO products(professional_id,name,price_cents,sold_by_weight370,available,created_at,updated_at) VALUES(?,'Mussarela411',4000,1,1,?,?)",(pid,m.now_iso(),m.now_iso())).lastrowid
    sid=open_sale(client,'pickup')
    assert change(client,sid,'item',product_id=weighted).status_code==400
    assert change(client,sid,'item',product_id=weighted,weight_grams=1200).status_code==200
    assert get(client,sid)['total_cents']==4800
    change(client,sid,'payment',method='pix',amount='48,00');change(client,sid,'close')
    with m.db() as c:
        day=m.datetime.now(m.SAO_PAULO_TZ).date()
        report=m.checkout_report411(c,pid,day)
        assert report['totals']['pickup']>=4800
        assert any(r['code']=='CX-'+str(sid) and r['kind']=='pickup' for r in report['rows'])
        assert sum(r['cents'] for r in report['rows'])==report['total']
    assert client.get('/painel/checkout?tab=summary').status_code==200
    page=client.get('/painel/checkout?tab=tables')
    assert page.status_code==200 and 'Menu de vendas' in page.text and 'Mesas abertas' in page.text and 'Mesas fechadas' in page.text
    assert 'Sistema checkout' in client.get('/painel').text


def test_two_tabs_cannot_open_duplicate_tables_or_duplicate_payments(checkout):
    from concurrent.futures import ThreadPoolExecutor
    from fastapi.testclient import TestClient
    m,client,pid,product,_=checkout
    name='Mesa concorrente '+secrets.token_hex(4)
    client.post('/painel/checkout/mesas',data={'name':name},follow_redirects=False)
    with m.db() as c:tid=c.execute('SELECT id FROM checkout_tables411 WHERE professional_id=? AND name=?',(pid,name)).fetchone()[0]
    def call(path,data):
        other=TestClient(m.app,headers={'Origin':'http://testserver','Accept':'application/json'},follow_redirects=False)
        other.cookies.set('nowup_session','merchant-test')
        try:return other.post(path,data=data)
        finally:other.close()
    with ThreadPoolExecutor(2) as pool:
        opened=list(pool.map(lambda _:call(f'/painel/checkout/mesas/{tid}/abrir',{}),range(2)))
    assert opened[0].headers['location']==opened[1].headers['location']
    sid=int(parse_qs(urlsplit(opened[0].headers['location']).query)['sale'][0]);change(client,sid,'item',product_id=product,quantity=2)
    version=get(client,sid)['version'];data={'action':'payment','method':'pix','amount':'5,00','version':version}
    with ThreadPoolExecutor(2) as pool:results=list(pool.map(lambda _:call(f'/painel/checkout/vendas/{sid}/alterar',data),range(2)))
    assert sorted(r.status_code for r in results)==[200,409]
    assert get(client,sid)['paid']==500


def test_report_counts_link_and_manual_once_by_fulfillment(checkout):
    m,client,pid,product,_=checkout
    day=m.datetime.now(m.SAO_PAULO_TZ).date()
    with m.db() as c:
        before=m.checkout_report411(c,pid,day)
        for kind,cents in [('delivery',1100),('pickup',900)]:
            c.execute("INSERT INTO orders(professional_id,customer_name,status,total_cents,created_at,updated_at,fulfillment_type,order_origin,payment_method) VALUES(?,'Link411','completed',?,?,?,?, 'external','pix')",(pid,cents,m.now_iso(),m.now_iso(),kind))
    sid=open_sale(client);change(client,sid,'item',product_id=product,quantity=2)
    change(client,sid,'payment',method='cash',amount='5,00')
    with m.db() as c:
        partial=m.checkout_report411(c,pid,day)
        assert partial['totals']['counter']==before['totals']['counter']
    change(client,sid,'payment',method='credit',amount='5,00');change(client,sid,'close')
    with m.db() as c:
        after=m.checkout_report411(c,pid,day)
        assert after['totals']['delivery']-before['totals']['delivery']==1100
        assert after['totals']['pickup']-before['totals']['pickup']==900
        assert after['totals']['counter']-before['totals']['counter']==1000
        assert after['total']-before['total']==3000
        assert sum(r['code']=='CX-'+str(sid) for r in after['rows'])==1
